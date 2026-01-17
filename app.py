from flask import Flask, request, jsonify
from analyze_reputation import ReputationAnalyzer

app = Flask(__name__)

@app.route('/analyze_reputation', methods=['POST'])
def analyze():
    data = request.json
    
    analyzer = ReputationAnalyzer(
        clinic_name=data['clinic_name'],
        clinic_location=data['clinic_location']
    )
    
    reviews = analyzer.scrape_google_reviews()
    
    if reviews:
        report = analyzer.generate_report_data()
        return jsonify(report), 200
    else:
        return jsonify({"error": "No reviews found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
