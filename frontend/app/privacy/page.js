export default function Privacy() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 py-12 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Privacy Policy</h1>
        
        <div className="space-y-6 text-gray-700">
          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-2">1. Introduction</h2>
            <p>
              MSRobot ("we," "us," "our") is committed to protecting your privacy and ensuring you have a positive experience on our platform. This Privacy Policy outlines our practices regarding data collection, use, and protection.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-2">2. What We Collect</h2>
            <p className="font-semibold">We collect the following information:</p>
            <ul className="list-disc list-inside space-y-2 ml-2">
              <li><strong>Chat Messages:</strong> Your questions and MSRobot's responses</li>
              <li><strong>Metadata:</strong> Confidence scores, timestamp, session ID</li>
              <li><strong>Interaction Data:</strong> Which tone you selected, follow-ups clicked</li>
            </ul>
            <p className="mt-3 font-semibold">We do NOT collect:</p>
            <ul className="list-disc list-inside space-y-2 ml-2">
              <li>Your name, email, or personal contact information</li>
              <li>Your IP address or precise location</li>
              <li>Device fingerprints or unique identifiers</li>
              <li>Sensitive personal data (passwords, financial info, etc.)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-2">3. Purpose of Collection</h2>
            <p>We collect your data to:</p>
            <ul className="list-disc list-inside space-y-2 ml-2">
              <li>Understand what questions users ask most frequently</li>
              <li>Improve MSRobot's responses and accuracy</li>
              <li>Identify gaps in the knowledge base</li>
              <li>Track service performance and reliability</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-2">4. Data Retention</h2>
            <p>
              Your chat data is retained for <strong>30 days</strong> and then automatically deleted. You can request deletion at any time by emailing <strong>selmi.ms1995@gmail.com</strong>.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-2">5. Data Protection</h2>
            <p>
              Your data is stored securely in MongoDB with industry-standard encryption. We do not share your data with third parties. Only the MSRobot administrator has access for improvement purposes.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-2">6. Your GDPR Rights</h2>
            <p>Under GDPR, you have the right to:</p>
            <ul className="list-disc list-inside space-y-2 ml-2">
              <li><strong>Access:</strong> Request a copy of your data</li>
              <li><strong>Deletion:</strong> Request permanent deletion ("right to be forgotten")</li>
              <li><strong>Opt-out:</strong> Decline data collection (click "Decline" on first load)</li>
              <li><strong>Withdraw Consent:</strong> Change your mind anytime</li>
            </ul>
            <p className="mt-3">
              To exercise any of these rights, email <strong>selmi.ms1995@gmail.com</strong> with your request.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-2">7. Consent</h2>
            <p>
              When you first visit MSRobot, you'll see a consent modal asking permission to collect data. You can:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-2">
              <li><strong>Accept:</strong> Allow data collection for improvement</li>
              <li><strong>Decline:</strong> Opt-out (chat still works, nothing is logged)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-2">8. Changes to This Policy</h2>
            <p>
              We may update this policy occasionally. The most recent version is always at https://msrobot.vercel.app/privacy. We'll notify users of significant changes via the consent modal.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-2">9. Contact</h2>
            <p>
              For questions about this privacy policy or to exercise your rights:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-2">
              <li>Email: <strong>selmi.ms1995@gmail.com</strong></li>
              <li>GitHub: <a href="https://github.com/meherms" className="text-blue-600 hover:underline">https://github.com/meherms</a></li>
            </ul>
          </section>

          <section className="mt-8 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-500">
              <strong>Last Updated:</strong> May 2026<br/>
              <strong>Status:</strong> GDPR Compliant
            </p>
          </section>
        </div>

        <div className="mt-8">
          <a 
            href="/" 
            className="inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Back to MSRobot
          </a>
        </div>
      </div>
    </div>
  );
}