// ChatWidget.jsx

import React, { useState, useEffect, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChatSocket } from "../hooks/useChatSocket";
import defaultConfig from "../config";
import { getSuggestedQuestions, extractCurrentTopic } from "../utils/dynamicQuestions";
import "./ChatWidget.css"; // Import CSS from the same directory

const FeedbackPrompt = ({ onYes, onNo }) => (
  <div
    style={{
      marginTop: 8,
      marginBottom: 8,
      background: "#f7f7f7",
      borderRadius: 8,
      padding: 12,
      display: "flex",
      alignItems: "center",
      gap: 12,
    }}
  >
    <span>Was this helpful?</span>
    <button
      style={{
        background: "#4caf50",
        color: "#fff",
        border: "none",
        borderRadius: 4,
        padding: "4px 12px",
        cursor: "pointer",
      }}
      onClick={onYes}
    >
      Yes
    </button>
    <button
      style={{
        background: "#f44336",
        color: "#fff",
        border: "none",
        borderRadius: 4,
        padding: "4px 12px",
        cursor: "pointer",
      }}
      onClick={onNo}
    >
      No
    </button>
  </div>
);

const ThankYouMessage = () => (
  <div
    style={{
      marginTop: 8,
      marginBottom: 8,
      background: "#e8f5e9",
      color: "#2e7d32",
      borderRadius: 8,
      padding: 12,
      display: "flex",
      alignItems: "center",
      gap: 12,
      animation: "fadeOut 2s ease-in-out forwards",
    }}
  >
    <span>Thank you for your feedback!</span>
  </div>
);

const FeedbackForm = ({ onClose, onSubmit }) => {
  const [issues, setIssues] = useState([]);
  const [otherText, setOtherText] = useState("");
  const [supportOption, setSupportOption] = useState("");

  const issueOptions = [
    { value: "off-topic", label: "The answer was off-topic" },
    { value: "too-short", label: "It was too short" },
    { value: "too-complex", label: "It was too complex" },
    { value: "different-help", label: "I need a different kind of help" },
    { value: "other", label: "Other:" },
  ];

  const handleIssueChange = (val) => {
    if (issues.includes(val)) {
      setIssues(issues.filter((i) => i !== val));
      if (val === "other") setOtherText("");
    } else {
      setIssues([...issues, val]);
    }
  };

  const canSubmit =
    issues.length > 0 &&
    supportOption;

  const handleSubmit = () => {
    const feedback = {
      issues,
      otherText: issues.includes("other") ? otherText : "",
      supportOption,
    };
    onSubmit(feedback);
  };

  return (
    <div
      style={{
        marginTop: 8,
        marginBottom: 8,
        background: "#fffbe6",
        border: "1px solid #ffe58f",
        borderRadius: 8,
        padding: 16,
        maxWidth: 400,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8 }}>
        What seems to be the issue?{" "}
        <span style={{ fontWeight: 400, fontSize: 13 }}>
          (Choose one or more)
        </span>
      </div>
      <div style={{ marginBottom: 12 }}>
        {issueOptions.map((opt) => (
          <div key={opt.value} style={{ marginBottom: 4 }}>
            <label>
              <input
                type="checkbox"
                checked={issues.includes(opt.value)}
                onChange={() => handleIssueChange(opt.value)}
                style={{ marginRight: 6 }}
              />
              {opt.label}
              {opt.value === "other" && issues.includes("other") && (
                <input
                  type="text"
                  value={otherText}
                  onChange={(e) => setOtherText(e.target.value)}
                  placeholder="Please specify"
                  style={{
                    marginLeft: 8,
                    padding: 2,
                    borderRadius: 4,
                    border: "1px solid #ccc",
                    width: 140,
                  }}
                />
              )}
            </label>
          </div>
        ))}
      </div>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>Would you like to:</div>
      <div style={{ marginBottom: 12 }}>
        <label>
          <input
            type="radio"
            name="support"
            value="rephrase"
            checked={supportOption === "rephrase"}
            onChange={() => setSupportOption("rephrase")}
            style={{ marginRight: 6 }}
          />
          Try rephrasing your question
        </label>
        <br />
        <label>
          <input
            type="radio"
            name="support"
            value="talk-exec"
            checked={supportOption === "talk-exec"}
            onChange={() => setSupportOption("talk-exec")}
            style={{ marginRight: 6 }}
          />
          Talk to a human executive
        </label>
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          style={{
            background: canSubmit ? "#0066cc" : "#ccc",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            padding: "4px 12px",
            cursor: canSubmit ? "pointer" : "not-allowed",
          }}
          onClick={handleSubmit}
          disabled={!canSubmit}
        >
          Submit
        </button>
        <button
          style={{
            background: "#eee",
            color: "#333",
            border: "none",
            borderRadius: 4,
            padding: "4px 12px",
            cursor: "pointer",
          }}
          onClick={onClose}
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

const styles = `
  @keyframes fadeOut {
    0% {
      opacity: 1;
    }
    70% {
      opacity: 1;
    }
    100% {
      opacity: 0;
    }
  }
`;

const styleSheet = document.createElement("style");
styleSheet.textContent = styles;
document.head.appendChild(styleSheet);

const ChatWidget = ({ config: userConfig }) => {
  // Merge config with defaults
  const cfg = { ...defaultConfig, ...userConfig };
  const triggerCount = Number.isInteger(cfg.showNumberOfQuestions)
    ? cfg.showNumberOfQuestions
    : 3;

  // Chat state
  const [chatHistory, setChatHistory] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [fullScreen, setFullScreen] = useState(false);
  const [feedback, setFeeback] = useState(false);

  // Scheduling form state
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [scheduleFormData, setScheduleFormData] = useState({
    name: "",
    phoneNumber: "",
    vehicleType: "",
  });
  const [scheduleFormSubmitted, setScheduleFormSubmitted] = useState(false);
  const [scheduleError, setScheduleError] = useState("");

  // Suggestions state
  const [usedQuestions, setUsedQuestions] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  // Feedback state
  const [feedbackState, setFeedbackState] = useState({
    showPrompt: false,
    showForm: false,
    lastAssistantIdx: null,
    submitted: false,
  });

  // Track session start time and location
  const [sessionStartTime, setSessionStartTime] = useState(Date.now());
  const [userLocation, setUserLocation] = useState(null);
  const [locationDisplay, setLocationDisplay] = useState("");
  
  // Function to get city name from coordinates
  const getCityFromCoordinates = async (latitude, longitude) => {
    try {
      const response = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json&addressdetails=1&accept-language=en`);
      if (response.ok) {
        const data = await response.json();
        const address = data.address;
        return address.city || address.town || address.village || address.municipality || address.county || address.state || null;
      }
    } catch (error) {
      console.error('Error getting city name:', error);
    }
    return null;
  };
  
  useEffect(() => {
    setSessionStartTime(Date.now());
    
    // Get location from localStorage if available
    const storedLocation = localStorage.getItem('user_location');
    if (storedLocation) {
      try {
        const location = JSON.parse(storedLocation);
        setUserLocation(location);
        
        // Get city name if coordinates are available
        if (location.latitude && location.longitude) {
          getCityFromCoordinates(location.latitude, location.longitude).then(cityName => {
            if (cityName) {
              setLocationDisplay(`📍 ${cityName}`);
            } else {
              setLocationDisplay(`📍 ${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`);
            }
          });
        }
      } catch (error) {
        console.error('Error parsing stored location:', error);
      }
    }
  }, []);

  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);

  // WebSocket connection
  const { sendMessage, connectionStatus, trackUserAction } = useChatSocket(
    setChatHistory,
    setStreaming,
    cfg.chatUrl
  );

  // Add session tracking on component mount
  useEffect(() => {
    // Track page load/refresh as a new session
    trackUserAction("session_start", {
      referrer: document.referrer,
      userAgent: navigator.userAgent,
    });
  }, [trackUserAction]);

  // Load initial suggestions
  useEffect(() => {
    const loadInitialSuggestions = async () => {
      setLoadingSuggestions(true);
      try {
        const initialQuestions = await getSuggestedQuestions([], '');
        setSuggestions(initialQuestions);
      } catch (error) {
        console.error('Error loading initial suggestions:', error);
        // Fallback to initial questions from config
        setSuggestions(cfg.initialSuggestedQuestions.slice(0, triggerCount));
      } finally {
        setLoadingSuggestions(false);
      }
    };
    
    loadInitialSuggestions();
  }, [cfg.initialSuggestedQuestions, triggerCount]);

  // Seed the initial system message
  useEffect(() => {
    setChatHistory([{ role: "system", text: cfg.introductionText }]);
  }, [cfg.introductionText]);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, suggestions, showScheduleForm]);

  // Auto-resize textarea - modified to respect fixed height
  useEffect(() => {
    if (textareaRef.current) {
      // Only adjust height if content exceeds the fixed height
      const scrollHeight = textareaRef.current.scrollHeight;
      const fixedHeight = 55; // Match the CSS height

      if (scrollHeight > fixedHeight) {
        // Allow content to scroll within the fixed height
        textareaRef.current.style.overflowY = "auto";
      } else {
        // Hide scrollbar when not needed
        textareaRef.current.style.overflowY = "hidden";
      }
    }
  }, [input]);

  // Update suggestions after each message
  const updateSuggestions = useCallback(async () => {
    if (chatHistory.length > 1) { // More than just the system message
      setLoadingSuggestions(true);
      try {
        const currentTopic = extractCurrentTopic(chatHistory);
        console.log('Updating suggestions with topic:', currentTopic, 'and history length:', chatHistory.length);
        const newSuggestions = await getSuggestedQuestions(chatHistory, currentTopic);
        console.log('New suggestions received:', newSuggestions);
        setSuggestions(newSuggestions);
      } catch (error) {
        console.error('Error updating suggestions:', error);
        // Keep current suggestions if update fails
      } finally {
        setLoadingSuggestions(false);
      }
    }
  }, [chatHistory]);

  // Single useEffect to handle suggestion updates
  useEffect(() => {
    if (streaming) {
      // Clear suggestions when streaming
      setSuggestions([]);
    } else if (chatHistory.length > 1) {
      // Update suggestions when streaming stops and we have conversation history
      const timer = setTimeout(() => {
        updateSuggestions();
      }, 500); // Small delay to ensure the response is complete
      
      return () => clearTimeout(timer);
    }
  }, [streaming, chatHistory, updateSuggestions]);

  // Show feedback prompt after each new assistant message
  useEffect(() => {
    // Find the last assistant message
    const lastIdx = [...chatHistory]
      .reverse()
      .findIndex((m) => m.role === "assistant");
    if (lastIdx !== -1) {
      const idx = chatHistory.length - 1 - lastIdx;
      if (feedbackState.lastAssistantIdx !== idx) {
        setFeedbackState({
          showPrompt: true,
          showForm: false,
          lastAssistantIdx: idx,
          submitted: false,
        });
      }
    }
    // eslint-disable-next-line
  }, [chatHistory]);

  // Toggle fullscreen mode
  const toggleFullScreen = () => {
    setFullScreen(!fullScreen);

    // Ensure chat scrolls to bottom after toggling fullscreen
    setTimeout(() => {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 300);
  };

  // Handle sending message
  const handleSendMessage = (text = input) => {
    if (!text.trim() || streaming) return;

    // Track user question
    trackUserAction("question_asked", { question: text });

    // Add user message to chat
    setChatHistory((prev) => [...prev, { role: "user", text }]);
    setStreaming(true);

    // Check if this is an appointment scheduling request
    const schedulingPhrases = [
      "schedule an appointment",
      "book an appointment",
      "make an appointment",
      "set up an appointment",
      "i need an appointment",
      "booking",
    ];

    const callbackPhrases = [
      "talk to someone",
      "talk to an expert",
      "speak with someone",
      "speak with an expert",
      "talk to a person",
      "speak to a person",
      "talk to a human",
      "speak to a human",
      "connect with expert",
      "connect with someone",
      "get expert advice",
      "need expert help",
      "want to talk",
      "want to speak",
      "need assistance",
      "need help",
      "contact expert",
      "contact someone",
      "call me back",
      "callback",
      "call back",
      "reach out",
      "get in touch",
      "contact me",
      "call me",
      "speak to me",
      "talk to me",
    ];

    const normalizedText = text.toLowerCase().trim();
    const isSchedulingRequest = schedulingPhrases.some((phrase) =>
      normalizedText.includes(phrase.toLowerCase())
    );
    const isCallbackRequest = callbackPhrases.some((phrase) =>
      normalizedText.includes(phrase.toLowerCase())
    );

    if (isCallbackRequest) {
      setShowScheduleForm(true);
      // Still send the message to get AI response
    }

    sendMessage({
      user_input: text,
    });

    // Clear input field if it's from the input box
    if (text === input) {
      setInput("");
    }
  };

  // Handle suggestion click
  const handleSuggestion = (question) => {
    handleSendMessage(question);
    setUsedQuestions((prev) => [...prev, question]);
  };

  // Handle Enter key press
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Handle schedule form input changes
  const handleScheduleFormChange = (e) => {
    const { name, value } = e.target;
    setScheduleFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    setScheduleError("");
  };

  // Handle schedule form submission
  const handleScheduleSubmit = async (e) => {
    e.preventDefault();

    // Validate form
    if (!scheduleFormData.name.trim()) {
      setScheduleError("Please enter your name");
      return;
    }
    if (!scheduleFormData.phoneNumber.trim()) {
      setScheduleError("Please enter your phone number");
      return;
    }
    if (!scheduleFormData.vehicleType) {
      setScheduleError("Please select your vehicle type");
      return;
    }

    try {
      // Capture lead in analytics
      const leadResponse = await fetch(
        `http://150.241.244.252:9006/analytics/leads`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: scheduleFormData.name,
            lead_type: "callback_request",
          }),
        }
      );

      if (!leadResponse.ok) {
        console.error("Failed to capture lead");
      }

      console.log("Lead captured");

      // Add callback request details to chat
      setChatHistory((prev) => [
        ...prev,
        {
          role: "user",
          text: `I'd like to request a callback with the following details:
- Name: ${scheduleFormData.name}
- Phone Number: ${scheduleFormData.phoneNumber}
- Vehicle Type: ${scheduleFormData.vehicleType}`,
        },
      ]);

      // Send callback request details to backend
      sendMessage({
        user_input: `Request callback for ${scheduleFormData.name} with phone number ${scheduleFormData.phoneNumber} for ${scheduleFormData.vehicleType}`,
        callback_details: {
          name: scheduleFormData.name,
          phone_number: scheduleFormData.phoneNumber,
          vehicle_type: scheduleFormData.vehicleType,
        },
      });

      setStreaming(true);
      setScheduleFormSubmitted(true);
      setShowScheduleForm(false);

      // Reset form after submission
      setTimeout(() => {
        setScheduleFormData({
          name: "",
          phoneNumber: "",
          vehicleType: "",
        });
        setScheduleFormSubmitted(false);
      }, 1000);
    } catch (error) {
      console.error("Error submitting callback request:", error);
      setScheduleError("Failed to submit callback request. Please try again.");
    }
  };

  // Add tracking to chatbot open function
  const handleChatbotOpen = () => {
    trackUserAction("chatbot_opened", { method: "button_click" });
    window.openChatbot();
  };

  const [showThankYou, setShowThankYou] = useState(false);

  const handleFeedbackYes = () => {
    setFeedbackState((f) => ({ ...f, showPrompt: false, submitted: true }));
    setShowThankYou(true);
    setTimeout(() => {
      setShowThankYou(false);
    }, 2000);
  };
  const handleFeedbackNo = () => {
    setFeedbackState((f) => ({ ...f, showPrompt: false, showForm: true }));
  };
  const handleFeedbackFormSubmit = (data) => {
    setFeedbackState((f) => ({ ...f, showForm: false, submitted: true }));
    
    // Hide suggestions immediately
    setSuggestions([]);
    
    // Show thank you message
    setShowThankYou(true);
    setTimeout(() => {
      setShowThankYou(false);
    }, 2000);
    
    // If user opted for human handover, log it
    if (data.supportOption === "talk-exec") {
      // Add support message to chat
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Thanks you for sharing feedback. You can connect with our support team between 9am-6pm on number 1800-102-1838 TOLL FREE NUMBER"
        }
      ]);

      const userId = localStorage.getItem("healthcare_user_id") || "";
      const sessionId = localStorage.getItem("healthcare_session_id") || "";
      // Find the last user message
      const lastUserMsg =
        [...chatHistory].reverse().find((m) => m.role === "user")?.text || "";
      fetch("http://150.241.244.252:9006/analytics/human_handover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          session_id: sessionId,
          issues: data.issues,
          other_text: data.otherText,
          support_option: data.supportOption,
          requested_at: new Date()
            .toISOString()
            .replace("T", " ")
            .replace("Z", "")
            .split(".")[0],
          last_message: lastUserMsg,
        }),
      }).catch(() => {});
    }
    
    // Restore suggestions after 3 seconds
    setTimeout(() => {
      updateSuggestions();
    }, 3000);
  };
  const handleFeedbackFormClose = () => {
    setFeedbackState((f) => ({ ...f, showForm: false }));
  };

  // Add this function inside ChatWidget
  const handleCloseChatbot = () => {
    const userId = localStorage.getItem("healthcare_user_id") || "";
    const sessionId = localStorage.getItem("healthcare_session_id") || "";
    const closedAt = new Date();
    const timeSpentSeconds = Math.floor((Date.now() - sessionStartTime) / 1000);
    const lastUserMsg =
      [...chatHistory].reverse().find((m) => m.role === "user")?.text || "";
    const lastBotMsg =
      [...chatHistory].reverse().find((m) => m.role === "assistant")?.text ||
      "";

    // Record chatbot close event
    fetch("http://150.241.244.252:9006/analytics/chatbot_close", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userId,
        session_id: sessionId,
        closed_at: closedAt
          .toISOString()
          .replace("T", " ")
          .replace("Z", "")
          .split(".")[0],
        time_spent_seconds: timeSpentSeconds,
        last_user_message: lastUserMsg,
        last_bot_message: lastBotMsg,
      }),
    }).catch(() => {});

    // Record session end event
    fetch("http://150.241.244.252:9006/analytics/session_end", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userId,
        session_id: sessionId,
        end_time: closedAt
          .toISOString()
          .replace("T", " ")
          .replace("Z", "")
          .split(".")[0],
        duration: timeSpentSeconds,
      }),
    }).catch(() => {});

    window.closeChatbot?.();
  };

  return (
    <div
      id="chatbot"
      className={`chat-widget${fullScreen ? " fullscreen" : ""}`}
      style={{ "--primary-color": cfg.primaryColor }}
    >
      <div className="chat-wrapper">
        {/* Header */}
        <div className="chat-header">
          <img
            src={cfg.companyLogo}
            alt={`${cfg.companyName} logo`}
            className="chat-logo"
          />
          <div className="header-info">
            <h2 className="chat-title">{cfg.companyName} AI Assistant</h2>
            {locationDisplay && (
              <div className="location-indicator" title="Location-based session">
                {locationDisplay}
              </div>
            )}
          </div>
          <div className="header-buttons">
            <button
              onClick={toggleFullScreen}
              className="fullscreen-button"
              aria-label="Toggle fullscreen"
            >
              {fullScreen ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M8 3v3a2 2 0 0 1-2 2H3" />
                  <path d="M21 8h-3a2 2 0 0 1-2-2V3" />
                  <path d="M3 16h3a2 2 0 0 1 2 2v3" />
                  <path d="M21 16h-3a2 2 0 0 1-2 2v3" />
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M8 3H5a2 2 0 0 0-2 2v3" />
                  <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
                  <path d="M3 16v3a2 2 0 0 0 2 2h3" />
                  <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
                </svg>
              )}
            </button>
            <button
              onClick={handleCloseChatbot}
              className="close-button"
              aria-label="Close chat"
            >
              ×
            </button>
          </div>
        </div>

        {/* Connection status indicator */}
        {connectionStatus !== "CONNECTED" && (
          <div
            className={`connection-status ${connectionStatus.toLowerCase()}`}
          >
            {connectionStatus === "CONNECTING"
              ? "Connecting..."
              : "Disconnected - Please check your connection"}
          </div>
        )}

        {/* Chat Content */}
        <div className="chat-content">
          {chatHistory.map((msg, i) => (
            <div
              key={i}
              className={`chat-block ${msg.role} ${msg.isError ? "error" : ""}`}
            >
              {msg.role !== "system" && (
                <div className="message-label">
                  {msg.role === "user"
                    ? "You"
                    : `${cfg.companyName} AI Assistant`}
                </div>
              )}
              <div
                className={`message ${
                  msg.role === "assistant" ? "assistant-message" : ""
                }`}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.text}
                </ReactMarkdown>
              </div>
              {/* Feedback prompt for the most recent assistant answer */}
              {msg.role === "assistant" &&
                i === feedbackState.lastAssistantIdx &&
                feedbackState.showPrompt &&
                !feedbackState.submitted && (
                  <FeedbackPrompt
                    onYes={handleFeedbackYes}
                    onNo={handleFeedbackNo}
                  />
                )}
              {msg.role === "assistant" &&
                i === feedbackState.lastAssistantIdx &&
                showThankYou && <ThankYouMessage />}
              {/* Feedback form if user said No */}
              {msg.role === "assistant" &&
                i === feedbackState.lastAssistantIdx &&
                feedbackState.showForm && (
                  <FeedbackForm
                    onClose={handleFeedbackFormClose}
                    onSubmit={handleFeedbackFormSubmit}
                  />
                )}
            </div>
          ))}

          {/* Appointment Scheduling Form */}
          {showScheduleForm && !streaming && (
            <div className="schedule-form-container">
              <h3>Request a Callback</h3>
              {scheduleError && (
                <div className="form-error">{scheduleError}</div>
              )}
              <form onSubmit={handleScheduleSubmit} className="schedule-form">
                <div className="form-group">
                  <label htmlFor="name">Full Name</label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={scheduleFormData.name}
                    onChange={handleScheduleFormChange}
                    placeholder="Enter your full name"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="phoneNumber">Phone Number</label>
                  <input
                    type="tel"
                    id="phoneNumber"
                    name="phoneNumber"
                    value={scheduleFormData.phoneNumber}
                    onChange={handleScheduleFormChange}
                    placeholder="Enter your phone number"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="vehicleType">Vehicle Type</label>
                  <select
                    id="vehicleType"
                    name="vehicleType"
                    value={scheduleFormData.vehicleType}
                    onChange={handleScheduleFormChange}
                  >
                    <option value="">Select your vehicle type</option>
                    <option value="Car">Car</option>
                    <option value="SUV">SUV</option>
                    <option value="Van">Van</option>
                    <option value="Bike">Bike</option>
                    <option value="Scooter">Scooter</option>
                    <option value="Truck">Truck</option>
                    <option value="Bus">Bus</option>
                    <option value="Agricultural">Agricultural</option>
                    <option value="Industrial">Industrial</option>
                    <option value="Earthmover">Earthmover</option>
                  </select>
                </div>

                <div className="form-actions">
                  <button
                    type="button"
                    className="cancel-button"
                    onClick={() => setShowScheduleForm(false)}
                  >
                    Cancel
                  </button>
                  <button type="submit" className="submit-button">
                    Request Callback
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Suggestions */}
          {!streaming && !showScheduleForm && suggestions.length > 0 && (
            <div className="suggestions">
              {suggestions.map((question, i) => (
                <button
                  key={i}
                  className="suggestion-button"
                  onClick={() => handleSuggestion(question)}
                  disabled={loadingSuggestions}
                >
                  {question}
                </button>
              ))}
            </div>
          )}

          {streaming && (
            <div className="chat-block assistant">
              <div className="message-label">
                {cfg.companyName} AI Assistant
              </div>
              <div className="message">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Area */}
        <div className="chat-input-area">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={cfg.inputPlaceholder}
            rows="1"
            className="chat-input"
            disabled={streaming}
            style={{ height: "55px" }}
          />
          <button
            className="send-button"
            onClick={() => {
              if (input.trim() && !streaming) {
                handleSendMessage();
              }
            }}
            disabled={!input.trim() || streaming}
            aria-label="Send message"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              width="24"
              height="24"
            >
              <path
                fill={streaming ? "#d7d7d7" : "#ffffff"}
                d="M22,11.7V12h-0.1c-0.1,1-17.7,9.5-18.8,9.1c-1.1-0.4,2.4-6.7,3-7.5C6.8,12.9,17.1,12,17.1,12H17c0,0,0-0.2,0-0.2c0,0,0,0,0,0c0-0.4-10.2-1-10.8-1.7c-0.6-0.7-4-7.1-3-7.5C4.3,2.1,22,10.5,22,11.7z"
              ></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatWidget;
