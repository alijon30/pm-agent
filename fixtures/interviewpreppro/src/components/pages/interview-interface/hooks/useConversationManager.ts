import { useCallback, useState } from 'react';
import { useConversation } from '@elevenlabs/react';
import { requestMicrophonePermission } from '../utils/permissions';
import { getSignedUrl } from '../utils/api';
import { USER_CONFIG } from '../constants/user';

export function useConversationManager() {
  const [isStarting, setIsStarting] = useState(false);
  
  const conversation = useConversation({
    onConnect: () => {
      console.log("Connected to conversation");
      setIsStarting(false);
    },
    onDisconnect: () => {
      console.log("Disconnected from conversation");
      setIsStarting(false);
    },
    onError: (error: string | Error) => {
      console.error("Conversation error:", error);
      setIsStarting(false);
      alert("An error occurred during the conversation");
    },
    onMessage: (message: string | object) => {
      console.log("Message received:", message);
    },
  });

  const startConversation = useCallback(async () => {
    if (isStarting) return;
    
    try {
      setIsStarting(true);
      console.log('Starting conversation...');
      
      const hasPermission = await requestMicrophonePermission();
      if (!hasPermission) {
        alert("Microphone permission is required to start the conversation");
        return;
      }
      
      const signedUrl = await getSignedUrl();
      
      await conversation.startSession({ 
        signedUrl,
        dynamicVariables: USER_CONFIG
      });
      
      console.log('Conversation started successfully');
    } catch (error) {
      console.error('Failed to start conversation:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      alert(`Failed to start conversation: ${errorMessage}`);
    } finally {
      setIsStarting(false);
    }
  }, [conversation, isStarting]);

  const stopConversation = useCallback(async () => {
    try {
      await conversation.endSession();
      console.log('Conversation ended');
    } catch (error) {
      console.error('Error ending conversation:', error);
    }
  }, [conversation]);

  return {
    conversation,
    startConversation,
    stopConversation,
    isStarting
  };
}