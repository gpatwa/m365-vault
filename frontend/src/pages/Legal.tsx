import { useState } from 'react';

type Tab = 'tos' | 'privacy';

export default function Legal() {
  const [tab, setTab] = useState<Tab>('tos');

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Legal</h1>

      <div className="flex gap-2 mb-6">
        {[
          { id: 'tos' as Tab, label: 'Terms of Service' },
          { id: 'privacy' as Tab, label: 'Privacy Policy' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.id ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border shadow-sm p-8 prose prose-sm max-w-none">
        {tab === 'tos' ? <TermsOfService /> : <PrivacyPolicy />}
      </div>
    </div>
  );
}

function TermsOfService() {
  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Terms of Service</h2>
      <p className="text-gray-400 text-sm mb-6">Last updated: March 2026</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">1. Acceptance of Terms</h3>
      <p className="text-gray-600 mb-4">By accessing or using Shieldio ("the Service"), you agree to be bound by these Terms of Service. If you do not agree, do not use the Service.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">2. Description of Service</h3>
      <p className="text-gray-600 mb-4">Shieldio provides backup, restore, and data protection services for Microsoft 365 workloads including Exchange Online, OneDrive for Business, SharePoint Online, Microsoft Teams, and Entra ID (Azure AD).</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">3. Account Registration</h3>
      <p className="text-gray-600 mb-4">You must provide accurate information during registration. You are responsible for maintaining the security of your account credentials and for all activities under your account.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">4. Microsoft 365 Authorization</h3>
      <p className="text-gray-600 mb-4">You authorize Shieldio to access your Microsoft 365 tenant data via Microsoft Graph API for the sole purpose of performing backup and restore operations. You retain all ownership rights to your data.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">5. Data Storage and Security</h3>
      <p className="text-gray-600 mb-4">All backup data is encrypted at rest using AES-256-GCM with per-tenant data encryption keys (DEKs) wrapped by a master key encryption key (KEK). Data is stored in your configured storage backend (Azure Blob Storage, S3-compatible, or local storage).</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">6. Data Retention</h3>
      <p className="text-gray-600 mb-4">Backup data is retained according to the SLA policies you configure. WORM (Write-Once-Read-Many) locked data cannot be deleted before the retention period expires. Legal hold data is retained indefinitely until the hold is released.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">7. Service Level</h3>
      <p className="text-gray-600 mb-4">We will use commercially reasonable efforts to maintain service availability. Backup schedules are best-effort and depend on Microsoft Graph API availability and rate limits.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">8. Limitation of Liability</h3>
      <p className="text-gray-600 mb-4">Shieldio is provided "as is" without warranty of any kind. We are not liable for data loss, service interruptions, or damages arising from the use of the Service. Our total liability is limited to the fees paid in the 12 months preceding the claim.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">9. Termination</h3>
      <p className="text-gray-600 mb-4">Either party may terminate at any time. Upon termination, your backup data will be retained for 30 days, after which it will be permanently deleted unless a longer retention period is required by applicable law or WORM policy.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">10. Changes to Terms</h3>
      <p className="text-gray-600 mb-4">We may update these terms at any time. Continued use of the Service after changes constitutes acceptance of the revised terms.</p>
    </div>
  );
}

function PrivacyPolicy() {
  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Privacy Policy</h2>
      <p className="text-gray-400 text-sm mb-6">Last updated: March 2026</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">1. Data We Collect</h3>
      <p className="text-gray-600 mb-2">We collect:</p>
      <ul className="list-disc list-inside text-gray-600 mb-4 space-y-1">
        <li><strong>Account data:</strong> username, email, name (provided during registration)</li>
        <li><strong>M365 tenant data:</strong> tenant ID, app registration credentials (encrypted)</li>
        <li><strong>Backup data:</strong> copies of your M365 data (emails, files, chats, directory objects)</li>
        <li><strong>Usage data:</strong> backup job history, API usage, login timestamps</li>
      </ul>

      <h3 className="text-lg font-semibold mt-6 mb-2">2. How We Use Your Data</h3>
      <ul className="list-disc list-inside text-gray-600 mb-4 space-y-1">
        <li>Performing backup and restore operations on your M365 data</li>
        <li>Monitoring backup health and detecting anomalies</li>
        <li>Generating reports and analytics</li>
        <li>Sending alert notifications (if configured)</li>
      </ul>

      <h3 className="text-lg font-semibold mt-6 mb-2">3. Data Storage</h3>
      <p className="text-gray-600 mb-4">Backup data is stored in your configured storage backend. For self-hosted deployments, data never leaves your infrastructure. For cloud deployments, data is stored in the Azure region you select.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">4. Encryption</h3>
      <p className="text-gray-600 mb-4">All backup data is encrypted at rest (AES-256-GCM) and in transit (TLS 1.2+). Each tenant has a unique data encryption key (DEK). Credentials are encrypted before storage.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">5. Data Sharing</h3>
      <p className="text-gray-600 mb-4">We do not sell, rent, or share your data with third parties. We do not access your backup data except as necessary to provide the Service or as required by law.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">6. Data Deletion</h3>
      <p className="text-gray-600 mb-4">You can request deletion of your account and backup data at any time via the tenant management interface. Data subject to WORM or legal hold will be retained per policy.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">7. GDPR Compliance</h3>
      <p className="text-gray-600 mb-4">For EU users: you have the right to access, correct, delete, and port your data. Contact us to exercise these rights. Our sensitive data scanner can help you identify personal data in your backups.</p>

      <h3 className="text-lg font-semibold mt-6 mb-2">8. Contact</h3>
      <p className="text-gray-600 mb-4">For privacy inquiries, contact: privacy@shieldio.com</p>
    </div>
  );
}
