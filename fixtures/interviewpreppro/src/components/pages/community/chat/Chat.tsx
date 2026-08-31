'use client';
import React, { useState } from 'react';
import ContactsSidebar from './components/ContactsSidebar';
import ChatArea from './components/ChatArea';
import MembersSidebar from './components/MembersSidebar';
import { Contact, ChatMessage, Member } from './types';

const Chat = () => {
  const [selectedContactId, setSelectedContactId] = useState(2);

  const contacts: Contact[] = [
    {
      id: 1,
      name: "Richard Wilson",
      message: "I will add you to our team, we...",
      avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=40&h=40&fit=crop&crop=face",
      isOnline: true,
      hasNewMessage: false
    },
    {
      id: 2,
      name: "ICG chat",
      message: "Jaden: Let's discuss this tom...",
      avatar: "IC",
      isOnline: false,
      hasNewMessage: true,
      isGroup: true
    },
    {
      id: 3,
      name: "Sarah Parker",
      message: "You: Ok, see you soon!",
      avatar: "https://images.unsplash.com/photo-1494790108755-2616b332c11c?w=40&h=40&fit=crop&crop=face",
      isOnline: true,
      hasNewMessage: false
    },
    {
      id: 4,
      name: "Abubakar Campbell",
      message: "You: Do you think we can do it?",
      avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=40&h=40&fit=crop&crop=face",
      isOnline: false,
      hasNewMessage: false
    },
    {
      id: 5,
      name: "Nathanael Jordan",
      message: "I'm busy",
      avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=40&h=40&fit=crop&crop=face",
      isOnline: true,
      hasNewMessage: false
    }
  ];

  const chatMessages: ChatMessage[] = [
    {
      id: 1,
      sender: "Richard Wilson",
      message: "added You",
      time: "6:15 pm",
      type: "system",
      avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face"
    },
    {
      id: 2,
      sender: "Conner Garcia",
      message: "Hey guys! Don't forget about our meeting next week! I'll be waiting for you at the 'Cozy Corner' cafe at 6:00 PM. Don't be late!",
      time: "6:25 pm",
      type: "message",
      avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=32&h=32&fit=crop&crop=face"
    },
    {
      id: 3,
      sender: "Richard Wilson",
      message: "Absolutely, I'll be there! Looking forward to catching up and discussing everything.",
      time: "6:25 pm",
      type: "message",
      avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face"
    },
    {
      id: 4,
      sender: "Lawrence Patterson",
      message: "@rwilson @jparker I have a new game plan",
      time: "6:25 pm",
      type: "message",
      avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=32&h=32&fit=crop&crop=face"
    },
    {
      id: 5,
      sender: "Jaden Parker",
      message: "Let's discuss this tomorrow",
      time: "6:25 pm",
      type: "message",
      avatar: "https://images.unsplash.com/photo-1494790108755-2616b332c11c?w=32&h=32&fit=crop&crop=face"
    }
  ];

  const members: Member[] = [
    { name: "Richard Wilson", role: "Admin", avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face", isOnline: true },
    { name: "You", avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=32&h=32&fit=crop&crop=face", isOnline: true },
    { name: "Jaden Parker", avatar: "https://images.unsplash.com/photo-1494790108755-2616b332c11c?w=32&h=32&fit=crop&crop=face", isOnline: false },
    { name: "Conner Garcia", avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=32&h=32&fit=crop&crop=face", isOnline: true },
    { name: "Lawrence Patterson", avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face", isOnline: false }
  ];

  const handleContactSelect = (contactId: number) => {
    setSelectedContactId(contactId);
  };

  const handleSendMessage = (message: string) => {
    console.log('Sending message:', message);
    // Here you would typically send the message to your backend
  };

  return (
    <div className="grid grid-cols-12 gap-6 max-h-screen ">
      <ContactsSidebar
        contacts={contacts}
        selectedContactId={selectedContactId}
        onContactSelect={handleContactSelect}
      />
      
      <ChatArea
        messages={chatMessages}
        onSendMessage={handleSendMessage}
      />
      
      <MembersSidebar
        members={members}
      />
    </div>
  );
};

export default Chat; 