#!/usr/bin/env python3
"""
Analyse de réputation automatisée pour cliniques dentaires
NuevoSmile QC - Janvier 2026 (SerpAPI Version)

Usage:
    python analyze_reputation.py "Dental Excellence" "Medellín"
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dotenv import load_dotenv

# Charger variables d'environnement
load_dotenv()

# Configuration
SERPAPI_KEY = os.getenv('SERPAPI_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


class ReputationAnalyzer:
    """Analyseur de réputation pour cliniques dentaires"""
    
    def __init__(self, clinic_name: str, clinic_location: str):
        self.clinic_name = clinic_name
        self.clinic_location = clinic_location
        self.reviews_data = []
        self.analysis_result = {}
        
    def scrape_google_reviews(self) -> List[Dict]:
        """Scrape Google Reviews via SerpAPI"""
        print(f"🔍 Scraping avis Google pour: {self.clinic_name}, {self.clinic_location}")
        
        if not SERPAPI_KEY:
            raise Exception("❌ SERPAPI_KEY non définie dans .env")
        
        # Étape 1: Trouver la clinique
        search_url = "https://serpapi.com/search"
        search_params = {
            "engine": "google_maps",
            "q": f"{self.clinic_name} {self.clinic_location} dental clinic Colombia",
            "type": "search",
            "api_key": SERPAPI_KEY
        }
        
        try:
            print("   🔎 Recherche de la clinique...")
            search_response = requests.get(search_url, params=search_params, timeout=30)
            search_response.raise_for_status()
            search_data = search_response.json()
            
            # Vérifier les résultats
            if not search_data.get('local_results'):
                print("   ❌ Aucune clinique trouvée")
                return []
            
            # Premier résultat
            place = search_data['local_results'][0]
            place_id = place.get('place_id')
            
            clinic_name = place.get('title', 'N/A')
            rating = place.get('rating', 0)
            reviews_count = place.get('reviews', 0)
            
            print(f"   ✅ Clinique trouvée: {clinic_name}")
            print(f"   ⭐ Note: {rating}/5 ({reviews_count} avis)")
            
            # Étape 2: Récupérer les avis détaillés
            print("   📥 Récupération des avis...")
            
            reviews_params = {
                "engine": "google_maps_reviews",
                "place_id": place_id,
                "api_key": SERPAPI_KEY,
                "hl": "es"
            }
            
            reviews_response = requests.get(search_url, params=reviews_params, timeout=30)
            reviews_response.raise_for_status()
            reviews_data = reviews_response.json()
            
            reviews_list = reviews_data.get('reviews', [])
            print(f"   ✅ {len(reviews_list)} avis récupérés!")
            
            # Formater les données pour compatibilité avec le reste du code
            clinic_data = {
                'name': clinic_name,
                'rating': rating,
                'reviews': reviews_count,
                'address': place.get('address', 'N/A'),
                'phone': place.get('phone', 'N/A'),
                'website': place.get('website', 'N/A'),
                'place_id': place_id,
                'reviews_data': self._format_reviews(reviews_list)
            }
            
            self.reviews_data = [clinic_data]
            return self.reviews_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur réseau: {e}")
            return []
        except Exception as e:
            print(f"❌ Erreur scraping: {e}")
            return []
    
    def _format_reviews(self, serpapi_reviews: List[Dict]) -> List[Dict]:
        """Convertir format SerpAPI vers format standard"""
        formatted = []
        
        for review in serpapi_reviews[:20]:  # Limiter à 20 pour l'analyse
            formatted.append({
                'review_text': review.get('snippet', ''),
                'review_rating': review.get('rating', 0),
                'review_datetime_utc': review.get('date', ''),
                'author_name': review.get('user', {}).get('name', 'Anonymous')
            })
        
        return formatted
    
    def analyze_with_ai(self, reviews: List[Dict]) -> Dict:
        """Analyse les avis avec OpenAI GPT-4"""
        if not reviews:
            print("⚠️  Aucun avis à analyser")
            return {}
        
        if not OPENAI_API_KEY:
            print("⚠️  OPENAI_API_KEY non définie - analyse IA désactivée")
            return {}
        
        print(f"🤖 Analyse IA de {len(reviews)} avis...")
        
        # Préparer le texte des avis
        reviews_text = []
        for i, review in enumerate(reviews[:20], 1):  # Max 20
            text = review.get('review_text', '')
            rating = review.get('review_rating', 0)
            if text:
                reviews_text.append(f"Avis {i} ({rating}★): {text}")
        
        if not reviews_text:
            print("⚠️  Aucun avis avec texte")
            return {}
        
        reviews_combined = "\n\n".join(reviews_text)
        
        prompt = f"""Tu es un expert en analyse de réputation pour cliniques dentaires.

Analyse ces avis Google d'une clinique dentaire en Colombie et fournis un rapport structuré.

AVIS À ANALYSER:
{reviews_combined}

INSTRUCTIONS:
1. Classifie chaque avis: Positif, Neutre, ou Négatif
2. Identifie les thèmes principaux (qualité, service, hygiène, délais, tarifs, complications)
3. Détecte RED FLAGS critiques (infections, arnaques, complications graves)
4. Extrais 3-5 citations représentatives
5. Recommandation: Go, No-Go, ou Investigate

FORMAT DE RÉPONSE (JSON strict):
{{
  "sentiment_distribution": {{
    "positif": <nombre>,
    "neutre": <nombre>,
    "negatif": <nombre>
  }},
  "themes": {{
    "qualite_travail": {{"mentions": <nombre>, "sentiment_moyen": <1-5>}},
    "service_client": {{"mentions": <nombre>, "sentiment_moyen": <1-5>}},
    "hygiene": {{"mentions": <nombre>, "sentiment_moyen": <1-5>}},
    "delais": {{"mentions": <nombre>, "sentiment_moyen": <1-5>}},
    "tarifs": {{"mentions": <nombre>, "sentiment_moyen": <1-5>}},
    "complications": {{"mentions": <nombre>, "sentiment_moyen": <1-5>}}
  }},
  "red_flags": [
    {{"type": "<type>", "severity": "low|medium|high", "description": "<description>"}}
  ],
  "citations_cles": [
    {{"type": "positif|negatif", "texte": "<citation>", "auteur": "<nom>"}}
  ],
  "recommandation": "Go|No-Go|Investigate",
  "raison_recommandation": "<explication>"
}}

IMPORTANT: Réponds UNIQUEMENT avec le JSON valide, rien d'autre."""

        try:
            import openai
            openai.api_key = OPENAI_API_KEY
            
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Tu es un expert en analyse de données et réputation dentaire."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Nettoyer le JSON
            if ai_response.startswith("```json"):
                ai_response = ai_response[7:]
            if ai_response.startswith("```"):
                ai_response = ai_response[3:]
            if ai_response.endswith("```"):
                ai_response = ai_response[:-3]
            ai_response = ai_response.strip()
            
            analysis = json.loads(ai_response)
            print("✅ Analyse IA complétée!")
            
            return analysis
            
        except Exception as e:
            print(f"❌ Erreur analyse IA: {e}")
            return {}
    
    def calculate_reputation_score(self, reviews_data: List[Dict], ai_analysis: Dict) -> int:
        """Calcule score réputation (0-100)"""
        if not reviews_data:
            return 0
        
        clinic_data = reviews_data[0]
        reviews = clinic_data.get('reviews_data', [])
        
        # 1. Note moyenne (40 points)
        avg_rating = clinic_data.get('rating', 0)
        score_rating = (avg_rating / 5.0) * 40
        
        # 2. Nombre d'avis (20 points)
        num_reviews = clinic_data.get('reviews', 0) or len(reviews)
        if num_reviews >= 100:
            score_volume = 20
        elif num_reviews >= 50:
            score_volume = 15
        elif num_reviews >= 20:
            score_volume = 10
        else:
            score_volume = 5
        
        # 3. Récence (15 points) - Simplifié car format date SerpAPI varie
        score_recency = 10  # Score neutre
        
        # 4. Tendance (15 points)
        score_trend = 10  # Score neutre par défaut
        
        # 5. Red flags (10 points)
        red_flags = ai_analysis.get('red_flags', [])
        high_severity = len([rf for rf in red_flags if rf.get('severity') == 'high'])
        medium_severity = len([rf for rf in red_flags if rf.get('severity') == 'medium'])
        
        if high_severity > 0:
            score_red_flags = 0
        elif medium_severity > 2:
            score_red_flags = 3
        elif medium_severity > 0:
            score_red_flags = 6
        else:
            score_red_flags = 10
        
        total_score = int(score_rating + score_volume + score_recency + score_trend + score_red_flags)
        
        print(f"""
📊 DÉTAIL SCORE:
   Note moyenne:    {score_rating:5.1f}/40
   Volume avis:     {score_volume:5}/20
   Récence:         {score_recency:5.1f}/15
   Tendance:        {score_trend:5}/15
   Red flags:       {score_red_flags:5}/10
   ──────────────────────────
   TOTAL:           {total_score:5}/100
        """)
        
        return total_score
    
    def generate_report_data(self) -> Dict:
        """Génère rapport complet"""
        if not self.reviews_data:
            print("❌ Pas de données à analyser")
            return {}
        
        clinic_data = self.reviews_data[0]
        reviews = clinic_data.get('reviews_data', [])
        
        # Analyse IA seulement s'il y a des avis
        ai_analysis = {}
        if reviews and len(reviews) > 0:
            ai_analysis = self.analyze_with_ai(reviews)
        else:
            print("⚠️  Pas d'avis détaillés - analyse de base seulement")
        
        # Score
        reputation_score = self.calculate_reputation_score(self.reviews_data, ai_analysis)
        
        # Recommandation
        recommendation = self._get_recommendation(reputation_score, ai_analysis)
        
        # Rapport complet
        report = {
            "clinic_name": clinic_data.get('name', self.clinic_name),
            "clinic_location": clinic_data.get('address', self.clinic_location),
            "analysis_date": datetime.now().isoformat(),
            "google_data": {
                "rating": clinic_data.get('rating', 0),
                "total_reviews": clinic_data.get('reviews', 0),
                "reviews_analyzed": len(reviews),
                "phone": clinic_data.get('phone', 'N/A'),
                "website": clinic_data.get('website', 'N/A'),
                "address": clinic_data.get('address', 'N/A'),
                "place_id": clinic_data.get('place_id', 'N/A')
            },
            "reputation_score": reputation_score,
            "ai_analysis": ai_analysis,
            "recommendation": recommendation,
            "raw_reviews_sample": reviews[:10]  # 10 premiers avis
        }
        
        self.analysis_result = report
        return report
    
    def _get_recommendation(self, score: int, ai_analysis: Dict) -> str:
        """Recommandation basée sur score et IA"""
        ai_rec = ai_analysis.get('recommandation', 'Investigate')
        red_flags = ai_analysis.get('red_flags', [])
        high_severity = [rf for rf in red_flags if rf.get('severity') == 'high']
        
        if high_severity:
            return "NO-GO"
        elif score >= 75 and ai_rec == "Go":
            return "GO"
        elif score < 60:
            return "NO-GO"
        else:
            return "INVESTIGATE"
    
    def save_report_json(self, filepath: str):
        """Sauvegarder rapport JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_result, f, indent=2, ensure_ascii=False)
        print(f"💾 Rapport sauvegardé: {filepath}")


def main():
    """Fonction principale"""
    if len(sys.argv) < 3:
        print("Usage: python analyze_reputation.py \"Nom Clinique\" \"Ville\"")
        print("Exemple: python analyze_reputation.py \"Dental Excellence\" \"Medellín\"")
        sys.exit(1)
    
    clinic_name = sys.argv[1]
    clinic_location = sys.argv[2]
    
    print("="*60)
    print("🦷 ANALYSE DE RÉPUTATION AUTOMATISÉE")
    print("    NuevoSmile QC - SerpAPI Version")
    print("="*60)
    print()
    
    # Analyser
    analyzer = ReputationAnalyzer(clinic_name, clinic_location)
    
    # Scraping
    reviews = analyzer.scrape_google_reviews()
    
    if not reviews:
        print("❌ Impossible de récupérer les avis")
        sys.exit(1)
    
    # Génération rapport
    report = analyzer.generate_report_data()
    
    if not report:
        print("❌ Impossible de générer le rapport")
        sys.exit(1)
    
    # Sauvegarder
    output_file = f"rapport_{clinic_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json"
    analyzer.save_report_json(output_file)
    
    # Afficher résumé
    print()
    print("="*60)
    print("📋 RÉSUMÉ ANALYSE")
    print("="*60)
    print(f"Clinique:        {report['clinic_name']}")
    print(f"Localisation:    {report['clinic_location']}")
    print(f"Note Google:     {report['google_data']['rating']}★")
    print(f"Nombre d'avis:   {report['google_data']['total_reviews']}")
    print(f"Avis analysés:   {report['google_data']['reviews_analyzed']}")
    print(f"Score:           {report['reputation_score']}/100")
    print(f"Recommandation:  {report['recommendation']}")
    print("="*60)
    
    # Red flags
    if report['ai_analysis'].get('red_flags'):
        print()
        print("⚠️  RED FLAGS DÉTECTÉS:")
        for rf in report['ai_analysis']['red_flags']:
            print(f"   - {rf.get('type', 'N/A')}: {rf.get('description', 'N/A')} (Sévérité: {rf.get('severity', 'N/A')})")
    
    print()
    print(f"✅ Analyse complétée! Rapport: {output_file}")


if __name__ == "__main__":
    main()
