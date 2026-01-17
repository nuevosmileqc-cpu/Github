from flask import Flask, request, jsonify
from analyze_reputation import ReputationAnalyzer
import os

app = Flask(__name__)

@app.route('/')
def home():
    """Page d'accueil"""
    return """
    <h1>🦷 NuevoSmile QC - API Analyse Réputation</h1>
    <p>API opérationnelle!</p>
    <h2>Endpoints disponibles:</h2>
    <ul>
        <li><strong>GET /health</strong> - Vérifier le statut</li>
        <li><strong>POST /analyze</strong> - Analyser une clinique</li>
    </ul>
    <h3>Exemple POST /analyze:</h3>
    <pre>
{
    "clinic_name": "Dental Excellence",
    "clinic_location": "Medellín"
}
    </pre>
    """

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "NuevoSmile Reputation Analyzer",
        "version": "1.0.0"
    }), 200

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Analyser une clinique dentaire
    
    Body JSON:
    {
        "clinic_name": "Nom de la clinique",
        "clinic_location": "Ville"
    }
    """
    try:
        # Récupérer les données
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Pas de données JSON reçues"
            }), 400
        
        clinic_name = data.get('clinic_name')
        clinic_location = data.get('clinic_location')
        
        if not clinic_name or not clinic_location:
            return jsonify({
                "error": "clinic_name et clinic_location sont requis"
            }), 400
        
        # Créer l'analyseur
        analyzer = ReputationAnalyzer(clinic_name, clinic_location)
        
        # Scraper les avis
        reviews = analyzer.scrape_google_reviews()
        
        if not reviews:
            return jsonify({
                "error": "Impossible de récupérer les avis"
            }), 404
        
        # Générer le rapport
        report = analyzer.generate_report_data()
        
        if not report:
            return jsonify({
                "error": "Impossible de générer le rapport"
            }), 500
        
        # Retourner le rapport
        return jsonify({
            "success": True,
            "data": report
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
```
