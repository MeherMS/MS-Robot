'use client';

import { useState, useEffect } from 'react';

export default function ConsentModal() {
  const [showModal, setShowModal] = useState(false);
  const [hasConsented, setHasConsented] = useState(null);

  useEffect(() => {
    // Check if user already consented in this session
    const sessionConsent = sessionStorage.getItem('msrobot_consent');
    
    if (sessionConsent === null) {
      // No consent in this session, show modal
      setShowModal(true);
    } else {
      // Already consented this session, don't show modal
      setHasConsented(sessionConsent === 'true');
    }
  }, []);

  const handleAccept = () => {
    sessionStorage.setItem('msrobot_consent', 'true');
    setHasConsented(true);
    setShowModal(false);
  };

  const handleDecline = () => {
    sessionStorage.setItem('msrobot_consent', 'false');
    setHasConsented(false);
    setShowModal(false);
  };

  if (!showModal) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full mx-4">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Data & Improvement</h2>
        
        <p className="text-gray-700 text-sm mb-4">
          MSRobot collects your messages to improve responses. Your data is protected under GDPR principles.
        </p>

        <div className="space-y-3 mb-6">
          <div className="text-sm text-gray-600">
            <p className="font-semibold mb-1">What we collect:</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Your questions and responses</li>
              <li>How confident each answer was</li>
              <li>When you asked (timestamp)</li>
            </ul>
          </div>

          <div className="text-sm text-gray-600">
            <p className="font-semibold mb-1">What we don't collect:</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Your name or email</li>
              <li>Your location or device info</li>
            </ul>
          </div>

          <p className="text-xs text-gray-500">
            <a href="/privacy" className="text-blue-600 hover:underline">
              Read our full Privacy Policy
            </a>
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleDecline}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition text-sm font-medium"
          >
            Decline
          </button>
          <button
            onClick={handleAccept}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium"
          >
            Accept
          </button>
        </div>
      </div>
    </div>
  );
}