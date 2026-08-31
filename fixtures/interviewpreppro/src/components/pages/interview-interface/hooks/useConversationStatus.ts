import { useMemo } from 'react';

interface ConversationStatusHook {
  isConnected: boolean;
  isSpeaking: boolean;
  statusText: string;
}

export function useConversationStatus(
  status: string, 
  isSpeaking: boolean
): ConversationStatusHook {
  return useMemo(() => {
    const connected = status === "connected";
    const speaking = isSpeaking;
    
    let text = "Disconnected";
    if (connected) {
      text = speaking ? "Agent is speaking" : "Agent is listening";
    }
    
    return {
      isConnected: connected,
      isSpeaking: speaking,
      statusText: text
    };
  }, [status, isSpeaking]);
}