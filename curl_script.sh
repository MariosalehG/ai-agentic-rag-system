time curl -s -X POST http://localhost:8000/api/v1/ask \
  -H 'content-type: application/json' \
  -d '{"query": "What are the two personas the small steering model uses in DoubtLess, and how is the difference between their logit vectors combined with the large model's logits to shorten its chain of thought?", "size": 5}' > /dev/null