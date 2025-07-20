from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
import mysql.connector
import re
from fastapi.responses import FileResponse
import os
import math
import json
from datetime import datetime
from collections import defaultdict, Counter
import unicodedata

# -----------------------------
# DATABASE CONFIG
# -----------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "mcd_kualalumpur"
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def query_db(sql: str, params=()) -> List[Dict]:
    """Execute database query and return results"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

# -----------------------------
# FASTAPI APP
# -----------------------------
app = FastAPI(
    title="McDonald's Outlet AI Assistant",
    version="3.0.0",
    description="Advanced AI-powered McDonald's outlet finder with RAG and NLP capabilities."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# SCHEMAS
# -----------------------------
class Outlet(BaseModel):
    id: int
    name: str
    address: Optional[str]
    waze_link: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    perks: Optional[List[str]] = []

class ChatRequest(BaseModel):
    question: str
    user_location: Optional[str] = None
    context: Optional[Dict] = None

class ChatResponse(BaseModel):
    answer: str
    outlets: Optional[List[Dict]] = None
    intent: str
    confidence: float
    reasoning: Optional[str] = None
    suggested_actions: Optional[List[str]] = None

# -----------------------------
# NLP & RAG UTILITIES
# -----------------------------
class TextProcessor:
    """Advanced text processing for NLP"""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for better matching"""
        text = unicodedata.normalize('NFKD', text.lower())
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """Extract important keywords from text"""
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'can', 'may', 'might', 'must', 'i', 'me',
            'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours'
        }
        
        words = TextProcessor.normalize_text(text).split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        keywords1 = set(TextProcessor.extract_keywords(text1))
        keywords2 = set(TextProcessor.extract_keywords(text2))
        
        if not keywords1 or not keywords2:
            return 0.0
        
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        
        return len(intersection) / len(union) if union else 0.0

class KnowledgeBase:
    """RAG-style knowledge base for McDonald's information"""
    
    def __init__(self):
        self.knowledge_vectors = {}
        self.location_aliases = {
            'kl': 'kuala lumpur',
            'klcc': 'kuala lumpur city centre',
            'bb': 'bukit bintang',
            'pj': 'petaling jaya',
            'mv': 'mid valley',
            'pavilion': 'pavilion kuala lumpur',
            'times square': 'berjaya times square',
            'lot 10': 'lot 10 shopping centre'
        }
        self.service_knowledge = {
            '24_hours': {
                'keywords': ['24', 'hour', 'hours', 'all', 'day', 'night', 'late', 'early', 'always', 'anytime'],
                'description': 'Outlets operating 24 hours a day',
                'perk_codes': ['24_HOURS']
            },
            'drive_thru': {
                'keywords': ['drive', 'thru', 'through', 'car', 'vehicle', 'takeaway', 'pickup', 'dt'],
                'description': 'Outlets with drive-thru service',
                'perk_codes': ['DRIVE_THRU']
            },
            'birthday_party': {
                'keywords': ['birthday', 'party', 'parties', 'celebration', 'event', 'kids', 'children', 'happy', 'meal', 'celebrate'],
                'description': 'Outlets supporting birthday party bookings',
                'perk_codes': ['BIRTHDAY_PARTY']
            },
            'wifi': {
                'keywords': ['wifi', 'internet', 'online', 'connection', 'work', 'study'],
                'description': 'Outlets with free WiFi access',
                'perk_codes': ['WIFI']
            },
            'mccafe': {
                'keywords': ['mccafe', 'coffee', 'cafe', 'espresso', 'latte', 'cappuccino'],
                'description': 'Outlets with McCafé service',
                'perk_codes': ['MCCAFE']
            },
            'delivery': {
                'keywords': ['delivery', 'mcdelivery', 'grab', 'foodpanda', 'deliver'],
                'description': 'Outlets with delivery service',
                'perk_codes': ['MCDELIVERY']
            },
            'breakfast': {
                'keywords': ['breakfast', 'morning', 'early'],
                'description': 'Outlets serving breakfast',
                'perk_codes': ['BREAKFAST']
            },
            'cashless': {
                'keywords': ['cashless', 'card', 'payment', 'digital'],
                'description': 'Outlets with cashless payment facilities',
                'perk_codes': ['CASHLESS_FACILITY']
            },
            'surau': {
                'keywords': ['surau', 'prayer', 'muslim', 'worship'],
                'description': 'Outlets with prayer facilities',
                'perk_codes': ['SURAU']
            }
        }
        self._build_knowledge_vectors()
        self._load_perks_from_db()
    
    def _load_perks_from_db(self):
        """Load available perks from database to update knowledge base"""
        try:
            perks = query_db("SELECT id, code, name FROM perks")
            self.available_perks = {perk['code']: perk for perk in perks}
        except Exception as e:
            print(f"Warning: Could not load perks from database: {e}")
            self.available_perks = {}
    
    def _build_knowledge_vectors(self):
        """Build knowledge vectors for semantic search"""
        for service, info in self.service_knowledge.items():
            self.knowledge_vectors[service] = {
                'keywords': info['keywords'],
                'vector': self._create_vector(info['keywords']),
                'description': info['description'],
                'perk_codes': info.get('perk_codes', [])
            }
    
    def _create_vector(self, keywords: List[str]) -> Dict[str, float]:
        """Create a simple vector representation"""
        vector = {}
        for keyword in keywords:
            vector[keyword] = 1.0
        return vector
    
    def search_knowledge(self, query: str) -> List[Tuple[str, float]]:
        """Search knowledge base using semantic similarity"""
        query_keywords = TextProcessor.extract_keywords(query)
        results = []
        
        for service, knowledge in self.knowledge_vectors.items():
            score = 0.0
            for keyword in query_keywords:
                if keyword in knowledge['vector']:
                    score += knowledge['vector'][keyword]
            
            if query_keywords:
                score = score / len(query_keywords)
            
            if score > 0:
                results.append((service, score))
        
        return sorted(results, key=lambda x: x[1], reverse=True)

class AgenticChatbot:
    """Agentic AI chatbot with reasoning capabilities"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.knowledge_base = KnowledgeBase()
        self.conversation_memory = []
        self.intent_weights = {
            'location_search': 0.3,
            'service_inquiry': 0.4,
            'general_info': 0.2,
            'navigation': 0.1
        }
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from user input"""
        entities = {
            'locations': [],
            'services': [],
            'time_references': [],
            'numbers': []
        }
        
        location_patterns = [
            r'\b(?:in|at|near|around)\s+([a-z\s]+?)(?:\s|$|,|\?|!)',
            r'\b(kuala lumpur|kl|klcc|bukit bintang|pavilion|mid valley|bangsar|mont kiara)\b',
            r'\b(petaling jaya|pj|subang|shah alam|damansara|cheras|ampang)\b'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text.lower())
            entities['locations'].extend([m.strip() for m in matches if m.strip()])
        
        text_lower = text.lower()
        for service, info in self.knowledge_base.service_knowledge.items():
            for keyword in info['keywords']:
                if keyword in text_lower:
                    entities['services'].append(service)
                    break  
        
        time_patterns = [r'\b(\d{1,2})\s*(?:am|pm)\b', r'\b(morning|afternoon|evening|night)\b']
        for pattern in time_patterns:
            matches = re.findall(pattern, text.lower())
            entities['time_references'].extend(matches)
        
        number_matches = re.findall(r'\b(\d+)\b', text)
        entities['numbers'] = [int(n) for n in number_matches]
        
        return entities
    
    def _reason_about_intent(self, query: str, entities: Dict) -> Tuple[str, float, str]:
        """Advanced reasoning to determine user intent"""
        reasoning_steps = []
        intent_scores = defaultdict(float)
        query_lower = query.lower()
        
        list_all_patterns = ['list all', 'show all', 'all outlets', 'all locations', 'every outlet', 'complete list']
        if any(pattern in query_lower for pattern in list_all_patterns):
            intent_scores['general_info'] += 0.9
            reasoning_steps.append("Detected 'list all' request - overriding other intents")
            return 'general_info', 0.9, " | ".join(reasoning_steps)
        
        if entities['services']:
            intent_scores['service_inquiry'] += 0.8 
            reasoning_steps.append(f"Detected service keywords: {entities['services']}")
        
        service_inquiry_keywords = [
            'allows', 'allow', 'support', 'supports', 'offer', 'offers', 'provide', 'provides', 
            'have', 'has', 'available', 'can i', 'do you', 'which', 'what', 'where can i'
        ]
        if any(kw in query_lower for kw in service_inquiry_keywords):
            intent_scores['service_inquiry'] += 0.6
            reasoning_steps.append("Found service inquiry keywords")
        
        if entities['locations']:
            intent_scores['location_search'] += 0.5
            reasoning_steps.append(f"Detected locations: {entities['locations']}")
        
        if entities['time_references']:
            intent_scores['service_inquiry'] += 0.3
            reasoning_steps.append(f"Detected time references: {entities['time_references']}")
        
        location_keywords = ['where', 'nearest', 'closest', 'find', 'locate', 'address']
        if any(kw in query_lower for kw in location_keywords) and not entities['services']:
            intent_scores['location_search'] += 0.5
            reasoning_steps.append("Found location search keywords")
        
        nav_keywords = ['direction', 'how to get', 'way to', 'navigate', 'route']
        if any(kw in query_lower for kw in nav_keywords):
            intent_scores['navigation'] += 0.7
            reasoning_steps.append("Found navigation keywords")
        
        general_keywords = ['list', 'show', 'tell me about', 'information']
        if any(kw in query_lower for kw in general_keywords) and not entities['services']:
            intent_scores['general_info'] += 0.4
            reasoning_steps.append("Found general information keywords")
        
        if not intent_scores:
            return 'general_info', 0.3, "No specific intent detected, defaulting to general information"
        
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = min(intent_scores[best_intent], 1.0)
        reasoning = " | ".join(reasoning_steps)
        
        return best_intent, confidence, reasoning
    
    def _generate_sql_query(self, intent: str, entities: Dict) -> Tuple[str, tuple]:
        """Generate appropriate SQL query based on intent and entities"""
        base_query = """
            SELECT DISTINCT 
                o.id, o.name, o.address, o.waze_link, o.latitude, o.longitude,
                GROUP_CONCAT(p.code) as perk_codes,
                GROUP_CONCAT(p.name) as perk_names
            FROM outlets o
            LEFT JOIN outlet_perks op ON o.id = op.outlet_id
            LEFT JOIN perks p ON op.perk_id = p.id
        """
        
        conditions = []
        params = []
        
        if entities['services']:  
            perk_conditions = []
            for service in entities['services']:
                if service in self.knowledge_base.service_knowledge:
                    perk_codes = self.knowledge_base.service_knowledge[service]['perk_codes']
                    for perk_code in perk_codes:
                        perk_conditions.append("p.code = %s")
                        params.append(perk_code)
            
            if perk_conditions:
                conditions.append(f"({' OR '.join(perk_conditions)})")
        
        if entities['locations']:
            location_conditions = []
            for location in entities['locations']:
                normalized_location = self.knowledge_base.location_aliases.get(location, location)
                location_conditions.append("o.address LIKE %s")
                params.append(f"%{normalized_location}%")
            
            if location_conditions:
                conditions.append(f"({' OR '.join(location_conditions)})")
        
        if conditions:
            sql = f"{base_query} WHERE {' AND '.join(conditions)} GROUP BY o.id, o.name, o.address, o.waze_link, o.latitude, o.longitude"
        else:
            sql = f"{base_query} GROUP BY o.id, o.name, o.address, o.waze_link, o.latitude, o.longitude"
        
        return sql, tuple(params)
    
    def _rank_outlets_by_relevance(self, outlets: List[Dict], query: str, entities: Dict) -> List[Dict]:
        """Rank outlets by relevance to user query"""
        if not outlets:
            return outlets
        
        scored_outlets = []
        
        for outlet in outlets:
            score = 0.0
            
            if entities['locations']:
                for location in entities['locations']:
                    if location.lower() in outlet.get('address', '').lower():
                        score += 0.5
            
            if entities['services']:
                outlet_perks = outlet.get('perk_codes', '') or ''
                for service in entities['services']:
                    if service in self.knowledge_base.service_knowledge:
                        perk_codes = self.knowledge_base.service_knowledge[service]['perk_codes']
                        for perk_code in perk_codes:
                            if perk_code in outlet_perks:
                                score += 0.8
                                break
            
            name_similarity = self.text_processor.calculate_similarity(
                query, outlet.get('name', '')
            )
            score += name_similarity * 0.3
            
            scored_outlets.append((outlet, score))
        
        scored_outlets.sort(key=lambda x: x[1], reverse=True)
        return [outlet for outlet, score in scored_outlets]
    
    def _format_outlet_perks(self, outlet: Dict) -> str:
        """Format outlet perks for display"""
        perk_codes = outlet.get('perk_codes', '')
        if not perk_codes:
            return ""
        
        perk_list = perk_codes.split(',') if perk_codes else []
        display_perks = []
        
        for perk in perk_list:
            perk = perk.strip() 
            if perk:
                if perk == '24_HOURS':
                    display_perks.append("24 Hours")
                elif perk == 'DRIVE_THRU':
                    display_perks.append("Drive-Thru")
                elif perk == 'WIFI':
                    display_perks.append("Free WiFi")
                elif perk == 'MCCAFE':
                    display_perks.append("McCafé")
                elif perk == 'MCDELIVERY':
                    display_perks.append("McDelivery")
                elif perk == 'BIRTHDAY_PARTY':
                    display_perks.append("Birthday Parties")
                elif perk == 'BREAKFAST':
                    display_perks.append("Breakfast")
                elif perk == 'CASHLESS_FACILITY':
                    display_perks.append("Cashless Payment")
                elif perk == 'SURAU':
                    display_perks.append("Prayer Facilities")
                elif perk == 'DESSERT_CENTER':
                    display_perks.append("Dessert Center")
                elif perk == 'DIGITAL_ORDER_KIOSK':
                    display_perks.append("Digital Ordering")
                else:
                    display_perks.append(perk.replace('_', ' ').title())
        
        return f" ({', '.join(display_perks)})" if display_perks else ""
    
    def _generate_response(self, intent: str, outlets: List[Dict], entities: Dict, query: str) -> Tuple[str, List[str]]:
        """Generate natural language response"""
        outlet_count = len(outlets) if outlets else 0
        suggested_actions = []
        
        def format_outlet_list(outlets_list):
            if not outlets_list:
                return ""
            
            formatted_list = []
            
            for outlet in outlets_list:
                name = outlet.get('name', 'Unknown')
                address = outlet.get('address', 'Address not available')
                
                perks_info = self._format_outlet_perks(outlet)
                
                formatted_list.append(f"• {name}{perks_info}\n  📍 {address}")
            
            return "\n\n" + "\n\n".join(formatted_list)
        
        if intent == 'service_inquiry':
            if 'birthday_party' in entities['services']:
                if outlet_count > 0:
                    response = f"🎉 Great news! I found {outlet_count} McDonald's outlet{'s' if outlet_count != 1 else ''} that offer birthday party services."
                    response += " These locations can host your special celebration with party packages, Happy Meals, decorations, and fun activities for kids!"
                    response += format_outlet_list(outlets)
                    suggested_actions = ["Book a party", "View party packages", "Get contact details", "Get directions"]
                else:
                    response = "I couldn't find any outlets specifically offering birthday party services in our database. However, many McDonald's outlets can accommodate celebrations - I'd recommend contacting them directly!"
                    suggested_actions = ["Find nearby outlets", "Contact customer service"]
            
            elif '24_hours' in entities['services']:
                if outlet_count > 0:
                    response = f"Great news! I found {outlet_count} McDonald's outlet{'s' if outlet_count != 1 else ''} that operate 24 hours."
                    if entities['locations']:
                        response += f" These are located around {', '.join(entities['locations'])}."
                    response += " Perfect for those late-night cravings or early morning breakfast!"
                    response += format_outlet_list(outlets)
                    suggested_actions = ["Get directions", "View menu", "Check other services"]
                else:
                    response = "I couldn't find any 24-hour McDonald's outlets in the specified area. Would you like me to show you outlets with extended hours instead?"
                    suggested_actions = ["Search nearby areas", "Find outlets with other services"]
            
            elif 'drive_thru' in entities['services']:
                if outlet_count > 0:
                    response = f"Perfect! I found {outlet_count} McDonald's outlet{'s' if outlet_count != 1 else ''} with Drive-Thru service."
                    response += " Great for quick and convenient ordering from your car!"
                    response += format_outlet_list(outlets)
                    suggested_actions = ["Get directions", "View Drive-Thru menu", "Check operating hours"]
                else:
                    response = "I couldn't find any Drive-Thru McDonald's outlets in the specified area."
                    suggested_actions = ["Search nearby areas", "Find all outlets"]
            
            else:
                service_names = []
                for service in entities['services']:
                    if service in self.knowledge_base.service_knowledge:
                        service_names.append(self.knowledge_base.service_knowledge[service]['description'])
                
                response = f"I found {outlet_count} outlet{'s' if outlet_count != 1 else ''} offering {', '.join(service_names) if service_names else 'the requested services'}."
                response += format_outlet_list(outlets)
                suggested_actions = ["Get directions", "View details", "Check other services"]
        
        elif intent == 'location_search':
            if outlet_count > 0:
                response = f"I located {outlet_count} McDonald's outlet{'s' if outlet_count != 1 else ''}"
                if entities['locations']:
                    response += f" near {', '.join(entities['locations'])}"
                response += ". Here are your options:"
                response += format_outlet_list(outlets)
                suggested_actions = ["Get directions", "View details", "Check services"]
            else:
                response = "I couldn't find any McDonald's outlets in that specific area. Let me show you the nearest alternatives."
                suggested_actions = ["Expand search area", "Show all outlets"]
        
        elif intent == 'navigation':
            if outlet_count > 0:
                response = f"I can help you navigate to {outlet_count} nearby McDonald's outlet{'s' if outlet_count != 1 else ''}. "
                response += "Each location includes Waze links for easy navigation."
                response += format_outlet_list(outlets)
                suggested_actions = ["Open in Waze", "Get walking directions", "View on map"]
            else:
                response = "I need more location information to provide navigation assistance."
                suggested_actions = ["Provide current location", "Search by address"]
        
        else: 
            if outlet_count > 0:
                response = f"Here's what I found: {outlet_count} McDonald's outlet{'s' if outlet_count != 1 else ''} in our database. "
                response += "Each location offers various services and amenities."
                response += format_outlet_list(outlets)
                suggested_actions = ["View all details", "Filter by services", "Find nearest"]
            else:
                response = "Welcome to the McDonald's Outlet Finder! I can help you find outlets, check services like 24-hour operation, Drive-Thru, and provide directions."
                suggested_actions = ["Find nearby outlets", "Check 24-hour locations", "Search by area"]
        
        return response, suggested_actions
    
    async def process_query(self, query: str, user_location: Optional[str] = None, context: Optional[Dict] = None) -> ChatResponse:
        """Main agentic processing pipeline"""
        try:
            self.conversation_memory.append({
                'query': query,
                'timestamp': datetime.now(),
                'user_location': user_location
            })
            
            entities = self._extract_entities(query)
            if user_location and not entities['locations']:
                entities['locations'].append(user_location)
            
            intent, confidence, reasoning = self._reason_about_intent(query, entities)
            
            sql, params = self._generate_sql_query(intent, entities)
            
            outlets = query_db(sql, params)
            
            outlets = self._rank_outlets_by_relevance(outlets, query, entities)
            
            response_text, suggested_actions = self._generate_response(intent, outlets, entities, query)
            
            return ChatResponse(
                answer=response_text,
                outlets=outlets,
                intent=intent,
                confidence=confidence,
                reasoning=reasoning,
                suggested_actions=suggested_actions
            )
            
        except Exception as e:
            return ChatResponse(
                answer="I apologize, but I encountered an issue processing your request. Could you please rephrase your question?",
                intent="error",
                confidence=0.0,
                reasoning=f"Error occurred: {str(e)}"
            )

chatbot = AgenticChatbot()

# -----------------------------
# ROUTES
# -----------------------------


# Serve index.html at root path
@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.get("/outlets", response_model=List[Outlet])
def list_outlets():
    """Get all outlets from DB with their perks"""
    sql = """
        SELECT DISTINCT 
            o.id, o.name, o.address, o.waze_link, o.latitude, o.longitude,
            GROUP_CONCAT(p.name) as perks
        FROM outlets o
        LEFT JOIN outlet_perks op ON o.id = op.outlet_id
        LEFT JOIN perks p ON op.perk_id = p.id
        GROUP BY o.id, o.name, o.address, o.waze_link, o.latitude, o.longitude
    """
    outlets = query_db(sql)
    
    for outlet in outlets:
        if outlet.get('perks'):
            outlet['perks'] = outlet['perks'].split(',')
        else:
            outlet['perks'] = []
    
    return outlets

@app.get("/outlets/{outlet_id}", response_model=Outlet)
def get_outlet(outlet_id: int):
    """Get single outlet by ID with perks"""
    sql = """
        SELECT DISTINCT 
            o.id, o.name, o.address, o.waze_link, o.latitude, o.longitude,
            GROUP_CONCAT(p.name) as perks
        FROM outlets o
        LEFT JOIN outlet_perks op ON o.id = op.outlet_id
        LEFT JOIN perks p ON op.perk_id = p.id
        WHERE o.id = %s
        GROUP BY o.id, o.name, o.address, o.waze_link, o.latitude, o.longitude
    """
    
    result = query_db(sql, (outlet_id,))
    
    if result:
        outlet = result[0]
        if outlet.get('perks'):
            outlet['perks'] = outlet['perks'].split(',')
        else:
            outlet['perks'] = []
        return outlet
    else:
        raise HTTPException(status_code=404, detail="Outlet not found.")

@app.get("/perks")
def list_perks():
    """Get all available perks"""
    return query_db("SELECT id, code, name FROM perks ORDER BY name")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Agentic AI chatbot with advanced NLP and reasoning capabilities
    """
    response = await chatbot.process_query(
        query=request.question,
        user_location=request.user_location,
        context=request.context
    )
    return response

@app.get("/chat/capabilities")
def get_chatbot_capabilities():
    """Get chatbot capabilities and knowledge base info"""
    return {
        "supported_intents": ["service_inquiry", "location_search", "navigation", "general_info"],
        "supported_services": list(chatbot.knowledge_base.service_knowledge.keys()),
        "location_aliases": chatbot.knowledge_base.location_aliases,
        "service_descriptions": {
            service: info["description"] 
            for service, info in chatbot.knowledge_base.service_knowledge.items()
        },
        "example_queries": [
            "Which outlets are open 24 hours?",
            "Find McDonald's with Drive-Thru near KLCC",
            "Show me outlets that support birthday parties",
            "Where can I find McCafé in Bukit Bintang?",
            "List all outlets with WiFi",
            "Find 24-hour outlets in Petaling Jaya"
        ],
        "capabilities": [
            "Natural language understanding",
            "Intent recognition and reasoning",
            "Service-based filtering",
            "Location-based search",
            "Contextual responses",
            "Relevance ranking"
        ]
    }

@app.get("/chat/memory")
def get_chat_memory():
    """Get chatbot conversation memory and statistics"""
    memory = chatbot.conversation_memory
    
    total_conversations = len(memory)
    recent_conversations = [
        conv for conv in memory[-10:]  
        if conv.get('timestamp')
    ]
    
    intent_stats = {}
    location_stats = {}
    
    for conv in memory:

        pass
    
    return {
        "total_conversations": total_conversations,
        "recent_conversations": [
            {
                "query": conv.get("query", ""),
                "timestamp": conv.get("timestamp").isoformat() if conv.get("timestamp") else None,
                "user_location": conv.get("user_location")
            }
            for conv in recent_conversations
        ],
        "memory_size": len(chatbot.conversation_memory),
        "knowledge_base_info": {
            "services_count": len(chatbot.knowledge_base.service_knowledge),
            "location_aliases_count": len(chatbot.knowledge_base.location_aliases)
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring service status"""
    try:
        test_query = "SELECT COUNT(*) as count FROM outlets LIMIT 1"
        db_result = query_db(test_query)
        db_status = "healthy" if db_result else "unhealthy"
        outlet_count = db_result[0]["count"] if db_result else 0
        
        chatbot_status = "healthy" if chatbot and hasattr(chatbot, 'knowledge_base') else "unhealthy"
        
        return {
            "status": "healthy" if db_status == "healthy" and chatbot_status == "healthy" else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "version": "3.0.0",
            "services": {
                "database": {
                    "status": db_status,
                    "outlet_count": outlet_count
                },
                "chatbot": {
                    "status": chatbot_status,
                    "memory_size": len(chatbot.conversation_memory) if chatbot else 0,
                    "knowledge_services": len(chatbot.knowledge_base.service_knowledge) if chatbot and hasattr(chatbot, 'knowledge_base') else 0
                }
            },
            "database_config": {
                "host": DB_CONFIG["host"],
                "database": DB_CONFIG["database"]
            }
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "version": "3.0.0",
            "error": str(e),
            "services": {
                "database": {"status": "error"},
                "chatbot": {"status": "error"}
            }
        }
