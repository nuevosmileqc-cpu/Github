#!/usr/bin/env python3
"""
Analyse de réputation automatisée pour cliniques dentaires
NuevoSmile QC - Janvier 2026

Usage:
    python analyze_reputation.py "Dental Excellence" "Medellín"
"""

import os
import sys
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dotenv import load_dotenv

# Charger variables d'environnement
load_dotenv()

# Configuration
OUTSCRAPER_API_KEY = os.getenv('OUTSCRAPER_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


class ReputationAnalyzer:
    """Analyseur de réputation pour cliniques dentaires"""
    
    def __init__(self, clinic_name: str, clinic_location: str):
        self.clinic_name = clinic_name
        self.clinic_location = clinic_location
        self.reviews_data = []
        self.analysis_result = {}
        
    def scrape_google_reviews(self) -> List[Dict]:
        """Scrape Google Reviews via Outscraper API"""
        print(f"🔍 Scraping avis Google pour: {self.clinic_name}, {self.clinic_location}")
        
        if not OUTSCRAPER_API_KEY:
            raise Exception("❌ OUTSCRAPER_API_KEY non définie dans .env")
        
        url = "https://api.app.outscraper.com/maps/search-v3"
        headers = {
            "X-API-KEY": OUTSCRAPER_API_KEY,
            "Content-Type": "application/json"
        }
        
        query = f"{self.clinic_name} {self.clinic_location} dental clinic Colombia"
        
        # Payload avec reviewsLimit pour obtenir les avis détaillés
        payload = {
            "query": query,
            "language": "es",
            "region": "CO",
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code not in [200, 202]:
                raise Exception(f"Status {response.status_code}: {response.text}")
            
            task_data = response.json()
            results_url = task_data.get('results_location')
            task_id = task_data.get('id')
            
            if not results_url:
                raise Exception("Pas de results_location reçu")
            
            print(f"⏳ Task {task_id} créé. En attente résultats...")
            
            # Polling pour résultats (max 90 secondes pour les reviews)
            for attempt in range(18):  # 18 x 5 = 90 secondes
                time.sleep(5)
                
                status_response = requests.get(
                    results_url,
                    headers={"X-API-KEY": OUTSCRAPER_API_KEY},
                    timeout=10
                )
                
                if status_response.status_code != 200:
                    continue
                
                status_data = status_response.json()
                
                if status_data.get('status') == 'Success':
                    print("✅ Scraping complété!")
                    data = status_data.get('data', [])
                    
                    # CORRECTION: Structure [[{...}]] au lieu de [{...}]
                    if data and isinstance(data, list) and len(data) > 0:
                        # Extraire le premier niveau de liste
                        inner_data = data[0]
                        
                        # Vérifier que c'est aussi une liste
                        if isinstance(inner_data, list) and len(inner_data) > 0:
                            # Extraire le dictionnaire de la clinique
                            clinic_data = inner_data[0]
                            
                            if isinstance(clinic_data, dict):
                                clinic_name = clinic_data.get('name', 'N/A')
                                rating = clinic_data.get('rating', 0)
                                reviews_count = clinic_data.get('reviews', 0)
                                
                                print(f"   ✅ Clinique: {clinic_name}")
                                print(f"   ⭐ Note: {rating}/5 ({reviews_count} avis)")
                                
                                # Vérifier si reviews_data existe
                                reviews_data = clinic_data.get('reviews_data', [])
                                if reviews_data and isinstance(reviews_data, list):
                                    num_reviews = len(reviews_data)
                                    print(f"   ✅ {num_reviews} avis détaillés récupérés!")
                                else:
                                    print(f"   ⚠️  Pas d'avis détaillés (seulement les stats)")
                                
                                # Retourner avec la structure correcte
                                self.reviews_data = [clinic_data]
                                return self.reviews_data
                            else:
                                print(f"   ❌ Élément n'est pas un dict: {type(clinic_data)}")
                                return []
                        else:
                            print(f"   ❌ data[0] n'est pas une liste: {type(inner_data)}")
                            return []
                    else:
                        print(f"   ❌ data vide ou invalide")
                        return []
                        
            raise Exception("⏱️ Timeout: scraping trop long (>90s)")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur réseau scraping: {e}")
            return []
        except Exception as e:
            print(f"❌ Erreur scraping: {e}")
            return []
    
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
        for i, review in enumerate(reviews[:50], 1):  # Max 50
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
        
        # 3. Récence (15 points)
        recent_reviews = 0
        six_months_ago = datetime.now() - timedelta(days=180)
        
        if reviews:
            for review in reviews:
                review_date_str = review.get('review_datetime_utc', '')
                if review_date_str:
                    try:
                        review_dt = datetime.strptime(review_date_str, "%Y-%m-%d %H:%M:%S")
                        if review_dt > six_months_ago:
                            recent_reviews += 1
                    except:
                        pass
            
            recent_ratio = recent_reviews / len(reviews) if len(reviews) > 0 else 0
            score_recency = recent_ratio * 15
        else:
            score_recency = 10  # Score neutre si pas de données de récence
        
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
                "address": clinic_data.get('address', 'N/A')
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
    print("    NuevoSmile QC")
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