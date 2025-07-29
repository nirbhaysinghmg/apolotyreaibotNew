from fastapi import APIRouter, HTTPException, Body
from datetime import datetime
from typing import Optional, Dict, Any
import mysql.connector
from mysql.connector import Error
import uuid
import json as json_lib
import hashlib

router = APIRouter()

# MySQL Configuration
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "nirbhay",
    "password": "Nirbhay@123",
    "database": "chatbot_analytics"
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")
    return None

def execute_query(query: str, params: tuple = None, fetch: bool = True, connection=None) -> Optional[Dict[str, Any]]:
    """Execute a query with optional connection for transactions"""
    close_connection = False
    cursor = None
    
    try:
        if connection is None:
            # Create new connection if not provided
            connection = get_db_connection()
            close_connection = True
            
        cursor = connection.cursor(dictionary=True)
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        if fetch:
            result = cursor.fetchall()
        else:
            if close_connection:
                connection.commit()
            result = None
            
        return result
    except Error as e:
        print(f"Error executing query: {e}")
        if close_connection and connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if close_connection and connection and connection.is_connected():
            connection.close()

def record_user_event(user_id: str, session_id: str, event_type: str, event_data: Dict = None):
    if not user_id:
        print("Warning: No user_id provided for analytics event")
        return

    timestamp = datetime.now().isoformat()
    page_url = event_data.get('page_url') if event_data else None
    duration = event_data.get('duration') if event_data else 0

    connection = None
    try:
        print(f"Recording analytics event: {event_type} for user {user_id} session {session_id}")
        connection = get_db_connection()
        connection.autocommit = False  # Enable transaction mode
        
        # Check if user exists
        user = execute_query(
            "SELECT * FROM users WHERE user_id = %s",
            (user_id,),
            fetch=True,
            connection=connection
        )

        if not user:
            print(f"Creating new user: {user_id}")
            # Create new user with all counters initialized to 0
            execute_query(
                """
                INSERT INTO users 
                  (user_id, first_seen_at, last_active_at, total_sessions, total_messages, total_duration, total_conversations, is_active)
                VALUES (%s, %s, %s, 0, 0, 0, 0, TRUE)
                """,
                (user_id, timestamp, timestamp),
                fetch=False,
                connection=connection
            )
        else:
            # Always update last_active_at for any event
            execute_query(
                """
                UPDATE users 
                SET last_active_at = %s
                WHERE user_id = %s
                """,
                (timestamp, user_id),
                fetch=False,
                connection=connection
            )

        # Update user stats based on event type
        if event_type == "session_start":
            print(f"Recording session start for user {user_id}")
            # Only update user stats, do NOT create session or conversation here
            execute_query(
                """
                UPDATE users 
                  SET total_sessions = total_sessions + 1,
                      is_active = TRUE,
                      last_page_url = %s
                WHERE user_id = %s
                """,
                (page_url, user_id),
                fetch=False,
                connection=connection
            )

        elif event_type == "question_asked":
            print(f"Recording question for user {user_id}: {event_data.get('question', '')[:50]}...")
            
            # Check if session exists
            session = execute_query(
                "SELECT * FROM sessions WHERE session_id = %s",
                (session_id,),
                fetch=True,
                connection=connection
            )
            
            conversation_id = None
            if not session:
                print(f"Creating new session: {session_id}")
                # Create new session with start_time = event_data['timestamp'] if available
                session_start_time = event_data.get('timestamp') if event_data and event_data.get('timestamp') else timestamp
                execute_query(
                    """
                    INSERT INTO sessions 
                      (session_id, user_id, start_time, page_url, message_count, status) 
                    VALUES (%s, %s, %s, %s, 0, 'active')
                    """,
                    (session_id, user_id, session_start_time, page_url),
                    fetch=False,
                    connection=connection
                )
                # Create new conversation for this session
                conversation_id = str(uuid.uuid4())
                execute_query(
                    """
                    INSERT INTO conversations 
                      (conversation_id, session_id, user_id, start_time, status)
                    VALUES (%s, %s, %s, %s, 'active')
                    """,
                    (conversation_id, session_id, user_id, session_start_time),
                    fetch=False,
                    connection=connection
                )
                print(f"Created new conversation: {conversation_id}")
            else:
                # Get the active conversation
                conversation = execute_query(
                    """
                    SELECT conversation_id 
                    FROM conversations 
                    WHERE session_id = %s AND status = 'active'
                    ORDER BY start_time DESC
                    LIMIT 1
                    """,
                    (session_id,),
                    fetch=True,
                    connection=connection
                )
                if conversation:
                    conversation_id = conversation[0]['conversation_id']
                    print(f"Using existing conversation: {conversation_id}")
                else:
                    # Create new conversation if none exists
                    conversation_id = str(uuid.uuid4())
                    execute_query(
                        """
                        INSERT INTO conversations 
                          (conversation_id, session_id, user_id, start_time, status)
                        VALUES (%s, %s, %s, %s, 'active')
                        """,
                        (conversation_id, session_id, user_id, timestamp),
                        fetch=False,
                        connection=connection
                    )
                    print(f"Created new conversation: {conversation_id}")
            
            # Insert the user's question
            if conversation_id:
                message_id = str(uuid.uuid4())
                execute_query(
                    """
                    INSERT INTO messages 
                    (message_id, conversation_id, user_id, message_type, content, timestamp)
                    VALUES (%s, %s, %s, 'user', %s, %s)
                    """,
                    (message_id, conversation_id, user_id, event_data.get('question', ''), timestamp),
                    fetch=False,
                    connection=connection
                )
                print(f"Inserted user message: {message_id}")
                
                # Update user message count
                execute_query(
                    """
                    UPDATE users 
                    SET total_messages = total_messages + 1
                    WHERE user_id = %s
                    """,
                    (user_id,),
                    fetch=False,
                    connection=connection
                    )

        elif event_type == "bot_response":
            print(f"Recording bot response for user {user_id}")
            # Find the active conversation for this session
            conv = execute_query(
                """
                SELECT conversation_id
                  FROM conversations
                 WHERE session_id = %s
                   AND status = 'active'
                 ORDER BY start_time DESC
                 LIMIT 1
                """,
                (session_id,),
                fetch=True,
                connection=connection
            )
            if conv:
                conversation_id = conv[0]["conversation_id"]
                # Insert the bot's response
                message_id = str(uuid.uuid4())
                execute_query(
                    """
                    INSERT INTO messages 
                      (message_id, conversation_id, user_id, message_type, content, timestamp)
                    VALUES (%s, %s, %s, 'bot', %s, %s)
                    """,
                    (message_id, conversation_id, user_id, event_data.get("response", ""), timestamp),
                    fetch=False,
                    connection=connection
                )
                print(f"Inserted bot message: {message_id}")
            else:
                print(f"Warning: No active conversation found for session {session_id}")

        elif event_type == "session_end":
            print(f"Recording session end for user {user_id}")
            # 1) Find the active conversation
            conv = execute_query(
                """
                SELECT conversation_id
                  FROM conversations
                 WHERE session_id = %s
                   AND status = 'active'
                 ORDER BY start_time DESC
                 LIMIT 1
                """,
                (session_id,),
                fetch=True,
                connection=connection
            )
            if conv:
                conversation_id = conv[0]["conversation_id"]
                # 2) Compute the duration in seconds, set conversation to "completed"
                execute_query(
                    """
                    UPDATE conversations
                      SET end_time = %s,
                          status   = 'completed',
                          duration = TIMESTAMPDIFF(SECOND, start_time, %s)
                     WHERE conversation_id = %s
                    """,
                    (timestamp, timestamp, conversation_id),
                    fetch=False,
                    connection=connection
                )
                # 3) Retrieve that duration we just computed
                result = execute_query(
                    """
                    SELECT duration
                      FROM conversations
                     WHERE conversation_id = %s
                    """,
                    (conversation_id,),
                    fetch=True,
                    connection=connection
                )
                if result:
                    session_duration = result[0]["duration"] or 0
                else:
                    session_duration = 0
                # 4) Update the user row:
                execute_query(
                    """
                    UPDATE users
                      SET is_active = FALSE,
                          last_active_at = %s,
                          total_duration = total_duration + %s,
                          total_conversations = total_conversations + 1
                    WHERE user_id = %s
                    """,
                    (timestamp, session_duration, user_id),
                    fetch=False,
                    connection=connection
                )

        elif event_type == "user_identified":
            execute_query(
                """
                UPDATE users 
                SET last_active_at = %s,
                    user_type = 'returning'
                WHERE user_id = %s
                """,
                (timestamp, user_id),
                fetch=False,
                connection=connection
            )

        # Commit the transaction
        if connection:
            connection.commit()
            print(f"Successfully committed analytics event: {event_type}")

    except Error as e:
        print(f"Error recording user event {event_type}: {e}")
        if connection:
            connection.rollback()
            print("Analytics transaction rolled back")
        # Don't raise HTTPException here to avoid breaking the main flow
    except Exception as e:
        print(f"Unexpected error recording user event {event_type}: {e}")
        if connection:
            connection.rollback()
            print("Analytics transaction rolled back")
    finally:
        if connection and connection.is_connected():
            connection.close()

def generate_short_id():
    """Generate a shorter, more readable ID"""
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8]

def generate_user_id():
    """Generate a shorter, meaningful user ID that fits in database column"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8]
    return f"user_{timestamp}_{random_part}"

# --- Analytics Endpoints ---

@router.get("/")
async def get_analytics():
    try:
        # Get total users
        total_users = execute_query("SELECT COUNT(*) as count FROM users")[0]['count']
        
        # Get total sessions
        total_sessions = execute_query("SELECT SUM(total_sessions) as count FROM users")[0]['count'] or 0
        
        # Get total questions
        total_questions = execute_query("SELECT SUM(total_messages) as count FROM users")[0]['count'] or 0
        
        # Get total chatbot opens
        total_opens = execute_query("SELECT COUNT(*) as count FROM users WHERE total_sessions > 0")[0]['count'] or 0
        
        # Get all users with their stats
        users = execute_query("""
            SELECT 
                u.*,
                COUNT(DISTINCT s.session_id) as session_count,
                AVG(s.duration) as avg_session_duration
            FROM users u
            LEFT JOIN sessions s ON u.user_id = s.user_id
            GROUP BY u.user_id
        """)
        
        users_data = {}
        for user in users:
            user_id = user['user_id']
            # Get user's sessions
            sessions = execute_query("""
                SELECT 
                    s.*,
                    COUNT(m.message_id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.session_id = m.conversation_id
                WHERE s.user_id = %s
                GROUP BY s.session_id
                ORDER BY s.start_time DESC
            """, (user_id,))
            
            sessions_data = []
            for session in sessions:
                # Get events for this session
                events = execute_query("""
                    SELECT 
                        message_type as type,
                        timestamp,
                        content as data
                    FROM messages 
                    WHERE conversation_id = %s
                    ORDER BY timestamp
                """, (session['session_id'],))
                
                events_data = []
                for event in events:
                    event_data = None
                    if event['data']:
                        try:
                            event_data = json_lib.loads(event['data'])
                        except:
                            event_data = event['data']
                            
                    events_data.append({
                        "type": event['type'],
                        "timestamp": event['timestamp'],
                        "data": event_data
                    })
                
                sessions_data.append({
                    "session_id": session['session_id'],
                    "start_time": session['start_time'],
                    "end_time": session['end_time'],
                    "duration": session['duration'],
                    "message_count": session['message_count'],
                    "events": events_data
                })
            
            users_data[user_id] = {
                "sessions": user['total_sessions'],
                "total_messages": user['total_messages'],
                "total_duration": user['total_duration'],
                "last_active": user['last_active_at'],
                "created_at": user['first_seen_at'],
                "is_active": user['is_active'],
                "session_history": sessions_data
            }
        
        return {
            "total_users": total_users,
            "total_sessions": total_sessions,
            "total_questions": total_questions,
            "total_chatbot_opens": total_opens,
            "users": users_data
        }
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions", tags=["analytics"])
async def get_session_analytics():
    try:
        # Get active sessions
        active_sessions = execute_query("""
            SELECT COUNT(*) as active_count 
            FROM sessions 
            WHERE status = 'active'
        """)[0]['active_count']

        # Get total sessions today (based on first message timestamp)
        today_sessions = execute_query("""
            SELECT COUNT(DISTINCT s.session_id) as today_count
            FROM sessions s
            JOIN messages m ON s.session_id = m.conversation_id
            WHERE DATE(m.timestamp) = CURDATE()
        """)[0]['today_count']

        # Get average session duration (based on first and last message timestamps)
        avg_duration_result = execute_query("""
            SELECT AVG(session_duration) as avg_duration FROM (
                SELECT 
                    TIMESTAMPDIFF(SECOND, 
                        (SELECT MIN(m.timestamp) FROM messages m WHERE m.conversation_id = s.session_id),
                        (SELECT MAX(m2.timestamp) FROM messages m2 WHERE m2.conversation_id = s.session_id)
                    ) as session_duration
                FROM sessions s
                WHERE EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = s.session_id)
            ) as durations
        """)
        avg_duration = avg_duration_result[0]['avg_duration'] if avg_duration_result else 0

        # Get recent sessions (by last message time)
        recent_sessions = execute_query("""
            SELECT 
                s.session_id,
                s.user_id,
                s.page_url,
                s.message_count,
                s.status
            FROM sessions s
            ORDER BY s.session_id DESC
            LIMIT 10
        """)

        # For each session, get first and last message timestamps and duration
        sessions_data = []
        for session in recent_sessions:
            times = execute_query(
                """
                SELECT 
                    MIN(timestamp) as start_time,
                    MAX(timestamp) as end_time
                FROM messages
                WHERE conversation_id = %s
                """,
                (session['session_id'],)
            )
            start_time = times[0]['start_time'] if times and times[0]['start_time'] else None
            end_time = times[0]['end_time'] if times and times[0]['end_time'] else None
            # Calculate duration
            if start_time and end_time:
                duration_query = execute_query(
                    "SELECT TIMESTAMPDIFF(SECOND, %s, %s) as duration",
                    (start_time, end_time)
                )
                duration = duration_query[0]['duration'] if duration_query else 0
            else:
                duration = 0
            sessions_data.append({
                "session_id": session['session_id'],
                "user_id": session['user_id'],
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "page_url": session['page_url'],
                "message_count": session['message_count'],
                "status": session['status']
            })

        return {
            "active_sessions": active_sessions or 0,
            "today_sessions": today_sessions or 0,
            "average_duration": round(avg_duration, 2) if avg_duration else 0,
            "recent_sessions": sessions_data
        }
    except Error as e:
        print(f"Error in session analytics: {str(e)}")
        return {
            "active_sessions": 0,
            "today_sessions": 0,
            "average_duration": 0,
            "recent_sessions": []
        }

@router.get("/conversations", tags=["analytics"])
async def get_conversation_analytics():
    try:
        # Get conversation statistics
        stats = execute_query("""
            SELECT 
                COUNT(*) as total_conversations,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_conversations,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_conversations,
                COUNT(CASE WHEN status = 'handover' THEN 1 END) as handover_conversations,
                AVG(duration) as avg_duration,
                COUNT(CASE WHEN message_type = 'user' THEN 1 END) as user_messages
            FROM conversations c
            LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            GROUP BY c.conversation_id
        """)[0]

        # Get recent conversations with message counts
        recent_conversations = execute_query("""
            SELECT 
                c.conversation_id,
                c.user_id,
                c.start_time,
                c.duration,
                c.status,
                COUNT(CASE WHEN m.message_type = 'user' THEN 1 END) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            GROUP BY c.conversation_id
            ORDER BY c.start_time DESC
            LIMIT 10
        """)

        return {
            "total_conversations": stats['total_conversations'] or 0,
            "active_conversations": stats['active_conversations'] or 0,
            "completed_conversations": stats['completed_conversations'] or 0,
            "handover_conversations": stats['handover_conversations'] or 0,
            "average_duration": round(stats['avg_duration'], 2) if stats['avg_duration'] else 0,
            "total_messages": stats['user_messages'] or 0,
            "recent_conversations": recent_conversations or []
        }
    except Error as e:
        print(f"Error in conversation analytics: {str(e)}")
        return {
            "total_conversations": 0,
            "active_conversations": 0,
            "completed_conversations": 0,
            "handover_conversations": 0,
            "average_duration": 0,
            "total_messages": 0,
            "recent_conversations": []
        }

@router.get("/messages", tags=["analytics"])
async def get_message_analytics():
    try:
        # Get message statistics - count each user-bot interaction as 1
        stats = execute_query("""
            SELECT 
                COUNT(DISTINCT CASE 
                    WHEN m1.message_type = 'user' AND m2.message_type = 'bot' 
                    AND m1.conversation_id = m2.conversation_id 
                    THEN m1.message_id 
                END) as total_messages,
                COUNT(CASE WHEN m1.message_type = 'user' THEN 1 END) as user_messages,
                COUNT(CASE WHEN m1.message_type = 'bot' THEN 1 END) as bot_messages,
                COUNT(CASE WHEN m1.message_type = 'system' THEN 1 END) as system_messages
            FROM messages m1
            LEFT JOIN messages m2 ON m1.conversation_id = m2.conversation_id 
                AND m2.message_type = 'bot'
                AND m2.timestamp > m1.timestamp
                AND NOT EXISTS (
                    SELECT 1 FROM messages m3 
                    WHERE m3.conversation_id = m1.conversation_id 
                    AND m3.message_type = 'bot'
                    AND m3.timestamp > m1.timestamp 
                    AND m3.timestamp < m2.timestamp
                )
        """)[0]

        # Get recent messages with details
        recent_messages = execute_query("""
            SELECT 
                m.message_id,
                m.conversation_id,
                m.user_id,
                m.message_type,
                m.content,
                m.timestamp
            FROM messages m
            ORDER BY m.timestamp DESC
            LIMIT 20
        """)

        return {
            "total_messages": stats['total_messages'] or 0,
            "user_messages": stats['user_messages'] or 0,
            "bot_messages": stats['bot_messages'] or 0,
            "system_messages": stats['system_messages'] or 0,
            "recent_messages": recent_messages or []
        }
    except Error as e:
        print(f"Error in message analytics: {str(e)}")
        return {
            "total_messages": 0,
            "user_messages": 0,
            "bot_messages": 0,
            "system_messages": 0,
            "recent_messages": []
        }

@router.get("/user/{user_id}", tags=["analytics"])
async def get_user_analytics_by_id(user_id: str):
    try:
        # Get user data
        user = execute_query("""
            SELECT 
                u.*,
                COUNT(DISTINCT s.session_id) as session_count,
                AVG(s.duration) as avg_session_duration
            FROM users u
            LEFT JOIN sessions s ON u.user_id = s.user_id
            WHERE u.user_id = %s
            GROUP BY u.user_id
        """, (user_id,))
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user[0]
        
        # Get user's sessions
        sessions = execute_query("""
            SELECT 
                s.*,
                COUNT(m.message_id) as message_count
            FROM sessions s
            LEFT JOIN messages m ON s.session_id = m.conversation_id
            WHERE s.user_id = %s
            GROUP BY s.session_id
            ORDER BY s.start_time DESC
        """, (user_id,))
        
        sessions_data = []
        for session in sessions:
            # Get events for this session
            events = execute_query("""
                SELECT 
                    message_type as type,
                    timestamp,
                    content as data
                FROM messages 
                WHERE conversation_id = %s
                ORDER BY timestamp
            """, (session['session_id'],))
            
            events_data = []
            for event in events:
                event_data = None
                if event['data']:
                    try:
                        event_data = json_lib.loads(event['data'])
                    except:
                        event_data = event['data']
                        
                events_data.append({
                    "type": event['type'],
                    "timestamp": event['timestamp'],
                    "data": event_data
                })
            
            sessions_data.append({
                "session_id": session['session_id'],
                "start_time": session['start_time'],
                "end_time": session['end_time'],
                "duration": session['duration'],
                "message_count": session['message_count'],
                "events": events_data
            })
        
        user_data = {
            "user_id": user['user_id'],
            "sessions": user['total_sessions'],
            "total_messages": user['total_messages'],
            "total_duration": user['total_duration'],
            "last_active": user['last_active_at'],
            "created_at": user['first_seen_at'],
            "is_active": user['is_active'],
            "total_conversations": user['total_conversations'],
            "session_history": sessions_data
        }
        
        return user_data
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/leads", tags=["analytics"])
async def capture_lead(lead_data: dict):
    try:
        # Generate a unique lead ID
        lead_id = str(uuid.uuid4())
        
        # Insert the lead into the analytics table
        execute_query(
            """
            INSERT INTO lead_analytics 
            (lead_id, lead_type, name, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                lead_id,
                'appointment_scheduled',
                lead_data.get('name', ''),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ),
            fetch=False
        )
        
        return {"status": "success", "lead_id": lead_id}
    except Error as e:
        print(f"Error capturing lead: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/leads", tags=["analytics"])
async def get_lead_analytics():
    try:
        # Get lead statistics
        stats = execute_query("""
            SELECT 
                COUNT(*) as total_leads,
                COUNT(CASE WHEN lead_type = 'appointment_scheduled' THEN 1 END) as scheduled_leads,
                DATE(created_at) as date,
                COUNT(*) as daily_leads
            FROM lead_analytics
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """)
        
        return {
            "total_leads": len(stats) or 0,
            "daily_leads": stats or []
        }
    except Error as e:
        print(f"Error in lead analytics: {str(e)}")
        return {
            "total_leads": 0,
            "daily_leads": []
        }

@router.post("/human_handover", tags=["analytics"])
async def record_human_handover(data: dict = Body(...)):
    try:
        print("Received handover data:", data)
        # Convert ISO 8601 to MySQL DATETIME
        requested_at = data.get('requested_at')
        if requested_at:
            try:
                if requested_at.endswith('Z'):
                    requested_at = requested_at[:-1]
                if '.' in requested_at:
                    requested_at = requested_at.split('.')[0]
                requested_at = requested_at.replace('T', ' ')
            except Exception as e:
                print("Error parsing requested_at:", e)
                requested_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            requested_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execute_query(
            """
            INSERT INTO human_handover
                (user_id, session_id, requested_at, issues, other_text, support_option, last_message, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            """,
            (
                data.get('user_id'),
                data.get('session_id'),
                requested_at,
                json_lib.dumps(data.get('issues', [])),
                data.get('other_text', ''),
                data.get('support_option', ''),
                data.get('last_message', ''),
            ),
            fetch=False
        )
        return {"status": "success"}
    except Error as e:
        print(f"Error recording human handover: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/human_handover", tags=["analytics"])
async def get_human_handover_analytics():
    try:
        count = execute_query("SELECT COUNT(*) as count FROM human_handover")[0]['count']
        recent = execute_query("""
            SELECT handover_id, user_id, session_id, requested_at, issues, other_text, support_option, status
            FROM human_handover
            ORDER BY requested_at DESC
            LIMIT 20
        """)
        return {"total_handover": count, "recent_handover": recent}
    except Error as e:
        print(f"Error in human handover analytics: {e}")
        return {"total_handover": 0, "recent_handover": []}

@router.post("/chatbot_close", tags=["analytics"])
async def record_chatbot_close(data: dict = Body(...)):
    try:
        closed_at = data.get('closed_at')
        if closed_at:
            try:
                if closed_at.endswith('Z'):
                    closed_at = closed_at[:-1]
                if '.' in closed_at:
                    closed_at = closed_at.split('.')[0]
                closed_at = closed_at.replace('T', ' ')
            except Exception as e:
                print("Error parsing closed_at:", e)
                closed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            closed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execute_query(
            """
            INSERT INTO chatbot_close_events
                (user_id, session_id, closed_at, time_spent_seconds, last_user_message, last_bot_message)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                data.get('user_id'),
                data.get('session_id'),
                closed_at,
                data.get('time_spent_seconds', 0),
                data.get('last_user_message', ''),
                data.get('last_bot_message', ''),
            ),
            fetch=False
        )
        return {"status": "success"}
    except Error as e:
        print(f"Error recording chatbot close: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session_end", tags=["analytics"])
async def record_session_end(data: dict = Body(...)):
    try:
        # Only update duration and status, do not update end_time
        execute_query(
            """
            UPDATE sessions
            SET duration = %s,
                status = 'completed'
            WHERE session_id = %s
            """,
            (
                data.get('duration', 0),
                data.get('session_id'),
            ),
            fetch=False
        )
        return {"status": "success"}
    except Error as e:
        print(f"Error recording session end: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events")
def get_events():
    try:
        return execute_query("SELECT * FROM events")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))