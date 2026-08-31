"use client";

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/pages/interview-interface/components/card';
import { cn } from '@/lib/utils';
import { ConversationOrb } from '@/components/pages/interview-interface/components/ConversationOrb';
import { ConversationControls } from '@/components/pages/interview-interface/components/ConversationControls';
import { useConversationManager } from '@/components/pages/interview-interface/hooks/useConversationManager';
import { useConversationStatus } from '@/components/pages/interview-interface/hooks/useConversationStatus';
import { keyframes } from '@/components/pages/interview-interface/styles/animations';

export function ConvAI() {
  const { 
    conversation, 
    startConversation, 
    stopConversation, 
    isStarting 
  } = useConversationManager();

  const { isConnected, isSpeaking, statusText } = useConversationStatus(
    conversation.status, 
    conversation.isSpeaking
  );

  return (
    <>
      <style>{keyframes}</style>
      <div className="flex justify-center items-center gap-x-4">
        <Card className={cn(
          "rounded-3xl glass-card transition-all duration-300 ease-in-out",
          isConnected && "glass-card-active animate-card-glow"
        )}>
          <CardContent>
            <CardHeader>
              <CardTitle className="text-center text-gray-600 transition-colors duration-300">
                {statusText}
              </CardTitle>
            </CardHeader>
            
            <div className="flex flex-col gap-y-4 text-center">
              <ConversationOrb 
                isConnected={isConnected} 
                isSpeaking={isSpeaking} 
              />

              <ConversationControls
                isConnected={isConnected}
                onStart={startConversation}
                onStop={stopConversation}
                isStarting={isStarting}
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}