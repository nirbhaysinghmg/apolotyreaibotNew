#!/usr/bin/env python3
"""
Comprehensive test scenarios for the Apollo Tyres conversational chatbot.
This script tests various conversation flows to ensure the chatbot responds appropriately.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.llm_setup import get_llm, SYSTEM_PROMPT
from app.vector_store import get_vector_store
from langchain.chains import ConversationalRetrievalChain

def test_conversational_scenarios():
    """Test various conversation scenarios to verify chatbot behavior"""
    
    print("🧪 Testing Apollo Tyres Conversational Chatbot - All Scenarios")
    print("=" * 70)
    
    # Initialize the LLM and vector store
    try:
        llm = get_llm()
        vector_store = get_vector_store()
        retriever = vector_store.as_retriever(search_kwargs={"k": 5})
        
        qa = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            combine_docs_chain_kwargs={"prompt": SYSTEM_PROMPT}
        )
        
        print("✅ Successfully initialized LLM and vector store")
        
    except Exception as e:
        print(f"❌ Error initializing: {e}")
        return
    
    # Test scenarios with expected behaviors
    test_scenarios = [
        {
            "category": "🚗 Passenger Car - Initial Recommendation",
            "question": "I have a Honda City, suggest tyres",
            "expected_indicators": [
                "honda", "city", "comfort", "alnac", "amazer", "driving", "city", "highway", "off-road"
            ],
            "expected_behavior": "Should acknowledge Honda City, suggest initial options, then ask about driving patterns"
        },
        {
            "category": "🚙 SUV - All-Terrain",
            "question": "I need tyres for my Mahindra XUV500",
            "expected_indicators": [
                "mahindra", "xuv", "apterra", "durability", "all-terrain", "driving", "city", "long drives", "off-roading"
            ],
            "expected_behavior": "Should mention Apterra range and ask about usage patterns"
        },
        {
            "category": "🏍️ Two-Wheeler",
            "question": "Suggest tyres for my Royal Enfield",
            "expected_indicators": [
                "royal enfield", "bike", "motorcycle", "performance", "comfort", "driving", "city", "highway"
            ],
            "expected_behavior": "Should acknowledge the bike and ask about riding patterns"
        },
        {
            "category": "🚛 Commercial Vehicle",
            "question": "I need tyres for my truck",
            "expected_indicators": [
                "truck", "commercial", "durability", "load", "longevity", "driving", "highway", "city"
            ],
            "expected_behavior": "Should ask about load carrying and usage patterns"
        },
        {
            "category": "💰 Budget Focus",
            "question": "I want affordable tyres for my Maruti Swift",
            "expected_indicators": [
                "maruti", "swift", "affordable", "budget", "economy", "driving", "city", "highway"
            ],
            "expected_behavior": "Should acknowledge budget concern and ask about priorities"
        },
        {
            "category": "🏁 Performance Focus",
            "question": "I want high-performance tyres for my sports car",
            "expected_indicators": [
                "sports car", "performance", "handling", "grip", "driving", "track", "highway"
            ],
            "expected_behavior": "Should focus on performance aspects and ask about usage"
        },
        {
            "category": "🌧️ Weather Specific",
            "question": "I need tyres for monsoon season",
            "expected_indicators": [
                "monsoon", "rain", "wet", "grip", "safety", "driving", "conditions"
            ],
            "expected_behavior": "Should ask about vehicle type and driving conditions"
        },
        {
            "category": "🛣️ Highway Focus",
            "question": "I do a lot of highway driving, suggest tyres",
            "expected_indicators": [
                "highway", "long drives", "comfort", "durability", "vehicle", "type"
            ],
            "expected_behavior": "Should ask about vehicle type and priorities"
        },
        {
            "category": "🏙️ City Focus",
            "question": "I only drive in the city, what tyres should I get?",
            "expected_indicators": [
                "city", "urban", "fuel efficiency", "comfort", "vehicle", "type"
            ],
            "expected_behavior": "Should ask about vehicle type and fuel efficiency priorities"
        },
        {
            "category": "🏔️ Off-Road",
            "question": "I do off-roading, suggest tyres",
            "expected_indicators": [
                "off-road", "terrain", "durability", "grip", "vehicle", "type"
            ],
            "expected_behavior": "Should ask about vehicle type and terrain conditions"
        },
        {
            "category": "🔧 Warranty Question",
            "question": "What is the warranty on Apollo tyres?",
            "expected_indicators": [
                "warranty", "5-year", "3-year", "manufacturing", "defects", "receipt"
            ],
            "expected_behavior": "Should provide warranty information directly"
        },
        {
            "category": "📍 Location Specific",
            "question": "I'm in Mumbai, where can I find Apollo dealers?",
            "expected_indicators": [
                "mumbai", "dealers", "authorized", "location", "nearby"
            ],
            "expected_behavior": "Should provide location-specific dealer information"
        },
        {
            "category": "📏 Size Specific",
            "question": "I need 205/55R16 tyres for my car",
            "expected_indicators": [
                "205/55r16", "size", "specifications", "vehicle", "type"
            ],
            "expected_behavior": "Should ask about vehicle type and driving patterns"
        },
        {
            "category": "⛽ Fuel Efficiency",
            "question": "I want fuel-efficient tyres",
            "expected_indicators": [
                "fuel efficiency", "mileage", "economy", "vehicle", "type", "driving"
            ],
            "expected_behavior": "Should ask about vehicle type and driving patterns"
        },
        {
            "category": "🔇 Quiet Ride",
            "question": "I want quiet tyres for a comfortable ride",
            "expected_indicators": [
                "quiet", "comfort", "noise", "ride", "vehicle", "type"
            ],
            "expected_behavior": "Should ask about vehicle type and usage patterns"
        }
    ]
    
    chat_history = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📝 Test {i}: {scenario['category']}")
        print(f"Question: {scenario['question']}")
        print(f"Expected: {scenario['expected_behavior']}")
        print("-" * 60)
        
        try:
            result = qa.invoke({
                "question": scenario["question"],
                "chat_history": chat_history,
                "user_location": "Mumbai, India"
            })
            
            answer = result["answer"]
            print(f"🤖 Bot Response: {answer}")
            
            # Check for expected indicators
            answer_lower = answer.lower()
            found_indicators = []
            missing_indicators = []
            
            for indicator in scenario["expected_indicators"]:
                if indicator.lower() in answer_lower:
                    found_indicators.append(indicator)
                else:
                    missing_indicators.append(indicator)
            
            # Check conversational indicators
            conversational_indicators = [
                "that's", "great", "nice", "perfect", "got it", "based on",
                "many", "drivers", "owners", "prefer", "excellent", "choice"
            ]
            
            is_conversational = any(indicator in answer_lower for indicator in conversational_indicators)
            
            # Check if it asks follow-up questions
            question_indicators = [
                "do you", "can i ask", "would you", "are you", "how do you",
                "what type", "mostly", "usually", "focused on"
            ]
            
            asks_questions = any(indicator in answer_lower for indicator in question_indicators)
            
            # Evaluation
            print(f"\n📊 Evaluation:")
            print(f"✅ Found indicators: {found_indicators}")
            if missing_indicators:
                print(f"⚠️  Missing indicators: {missing_indicators}")
            
            if is_conversational:
                print("✅ Response is conversational and friendly")
            else:
                print("⚠️  Response might be too formal")
                
            if asks_questions:
                print("✅ Asks follow-up questions appropriately")
            else:
                print("⚠️  Doesn't ask follow-up questions")
            
            # Update chat history
            chat_history.append((scenario["question"], answer))
            
        except Exception as e:
            print(f"❌ Error in test {i}: {e}")
    
    print("\n🎯 Test Summary:")
    print("The chatbot should demonstrate:")
    print("1. ✅ Acknowledges vehicles positively")
    print("2. ✅ Suggests initial Apollo options")
    print("3. ✅ Asks relevant follow-up questions")
    print("4. ✅ Maintains conversational tone")
    print("5. ✅ Provides location-specific information")
    print("6. ✅ Handles different vehicle types appropriately")
    print("7. ✅ Addresses specific requirements (budget, performance, etc.)")
    print("\n✅ Comprehensive scenario testing completed!")

def test_conversation_flow():
    """Test a complete conversation flow"""
    
    print("\n🔄 Testing Complete Conversation Flow")
    print("=" * 50)
    
    try:
        llm = get_llm()
        vector_store = get_vector_store()
        retriever = vector_store.as_retriever(search_kwargs={"k": 5})
        
        qa = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            combine_docs_chain_kwargs={"prompt": SYSTEM_PROMPT}
        )
        
        # Simulate a complete conversation
        conversation_steps = [
            "I have a Mahindra XUV500, suggest tyres",
            "Mostly city driving with some highway trips",
            "Fuel efficiency is my priority",
            "Budget is around 5000-8000 per tyre"
        ]
        
        chat_history = []
        
        for i, step in enumerate(conversation_steps, 1):
            print(f"\n👤 User {i}: {step}")
            
            result = qa.invoke({
                "question": step,
                "chat_history": chat_history,
                "user_location": "Delhi, India"
            })
            
            answer = result["answer"]
            print(f"🤖 Bot {i}: {answer}")
            
            chat_history.append((step, answer))
        
        print("\n✅ Complete conversation flow tested successfully!")
        
    except Exception as e:
        print(f"❌ Error in conversation flow: {e}")

if __name__ == "__main__":
    test_conversational_scenarios()
    test_conversation_flow() 