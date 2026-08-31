import React from 'react';
import { Button } from './button';
import { cn } from '../../../../lib/utils';

interface ConversationControlsProps {
  isConnected: boolean;
  onStart: () => void;
  onStop: () => void;
  isStarting?: boolean;
}

export const ConversationControls: React.FC<ConversationControlsProps> = ({
  isConnected,
  onStart,
  onStop,
  isStarting = false
}) => {
  return (
    <div className="flex flex-col gap-y-4">
      <Button
        variant="outline"
        className={cn(
          "rounded-full transition-all duration-300",
          "bg-white border-white/30 text-black",
          "hover:bg-emerald-500 hover:border-white hover:text-white",
          "backdrop-blur-sm",
          "disabled:opacity-50 disabled:cursor-not-allowed"
        )}
        size="lg"
        disabled={isConnected || isStarting}
        onClick={onStart}
      >
        {isStarting ? "Starting..." : "Start conversation"}
      </Button>
      
      <Button
        variant="outline"
        className={cn(
          "rounded-full transition-all duration-300",
          "bg-white border-white/30 text-black",
          "hover:bg-red-500 hover:border-red-400 hover:text-red-100",
          "backdrop-blur-sm",
          "disabled:opacity-50 disabled:cursor-not-allowed"
        )}
        size="lg"
        disabled={!isConnected}
        onClick={onStop}
      >
        End conversation
      </Button>
    </div>
  );
};