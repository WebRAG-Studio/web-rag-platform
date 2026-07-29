from app.core.conversation import ConversationStore


def test_follow_up_is_scoped_to_site_and_session():
    memory = ConversationStore()
    memory.remember("site-a", "one", "Explain the safety manual")
    assert "safety manual" in memory.resolve("site-a", "one", "What does it require?")
    assert memory.resolve("site-b", "one", "What does it require?") == "What does it require?"
    assert memory.resolve("site-a", "two", "What does it require?") == "What does it require?"


def test_new_standalone_question_does_not_inherit_topic():
    memory = ConversationStore()
    memory.remember("site-a", "one", "Explain the safety manual")
    assert memory.resolve("site-a", "one", "What is the return policy?") == "What is the return policy?"
