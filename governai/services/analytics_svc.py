from api.schemas import RawPredictionPayload

def calculate_drift(raw_prediction: RawPredictionPayload) -> float:
    """
    Simulates calculating semantic drift from a raw prediction.
    In a real system, this would compute the distance between the input embeddings 
    and a baseline reference set, or measure output distribution KL divergence.
    For this demo, we use statistical proxies.
    """
    score = 0.0
    
    # Proxy 1: Low confidence models often indicate drifting input space
    if raw_prediction.confidence_score is not None:
        score += (1.0 - raw_prediction.confidence_score) * 0.2
        
    # Proxy 2: Anomalous input lengths often indicate prompt injection or out-of-domain data
    if raw_prediction.input_text:
        length = len(raw_prediction.input_text)
        if length < 20 or length > 500:
            score += 0.15
            
    return round(score, 3)

def calculate_bias(raw_prediction: RawPredictionPayload) -> float:
    """
    Simulates a fairness/bias calculation on raw prediction data.
    In reality, this would evaluate protected class representation across a batch of inferences.
    For this demo, we use simple keyword flagging to simulate bias.
    """
    score = 0.0
    
    if raw_prediction.input_text:
        sensitive_words = ["gender", "race", "age", "religion", "female", "male", "nationality"]
        text_lower = raw_prediction.input_text.lower()
        matches = sum(1 for w in sensitive_words if w in text_lower)
        score += (matches * 0.08)
        
    return min(round(score, 3), 1.0)
