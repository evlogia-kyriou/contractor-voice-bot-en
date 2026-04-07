from prometheus_client import Counter, Histogram, Gauge

CALLS_TOTAL = Counter(
    "voice_bot_calls_total",
    "Total number of inbound calls handled",
)

INTENT_COUNTER = Counter(
    "voice_bot_intent_total",
    "Total intent classifications by type",
    ["intent"],
)

AGENT_COUNTER = Counter(
    "voice_bot_agent_total",
    "Total agent invocations by agent name",
    ["agent"],
)

BOOKINGS_TOTAL = Counter(
    "voice_bot_bookings_total",
    "Total successful calendar bookings",
)

SMS_TOTAL = Counter(
    "voice_bot_sms_total",
    "Total SMS notifications sent",
    ["channel", "recipient"],
)

RESPONSE_LATENCY = Histogram(
    "voice_bot_response_latency_seconds",
    "Response latency in seconds by agent",
    ["agent"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

ACTIVE_CALLS = Gauge(
    "voice_bot_active_calls",
    "Number of currently active calls",
)

RAG_ROUGE_SCORE = Gauge(
    "voice_bot_rag_rouge_score",
    "Latest RAG RougeL score",
)


def record_call_start():
    CALLS_TOTAL.inc()
    ACTIVE_CALLS.inc()


def record_call_end():
    ACTIVE_CALLS.dec()


def record_intent(intent: str):
    INTENT_COUNTER.labels(intent=intent).inc()


def record_agent(agent: str, latency: float):
    AGENT_COUNTER.labels(agent=agent).inc()
    RESPONSE_LATENCY.labels(agent=agent).observe(latency)


def record_booking():
    BOOKINGS_TOTAL.inc()


def record_sms(channel: str, recipient: str):
    SMS_TOTAL.labels(channel=channel, recipient=recipient).inc()


def record_rag_score(score: float):
    RAG_ROUGE_SCORE.set(score)