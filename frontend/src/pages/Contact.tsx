import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Shield, Mail, Github, Linkedin, ArrowRight, Send, Calendar } from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { appUrl } from '../utils/appUrl';

export default function Contact() {
  const [form, setForm] = useState({ name: '', email: '', company: '', message: '' });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // In production: POST to /api/contact or email service
    window.location.href = `mailto:hello@kavachiq.com?subject=Contact from ${form.name} (${form.company})&body=${encodeURIComponent(form.message)}`;
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Helmet>
        <title>Contact KavachIQ — Get in Touch</title>
        <meta name="description" content="Contact KavachIQ for Microsoft 365 data protection questions, demos, or partnership inquiries. Open-source SaaS backup platform." />
        <link rel="canonical" href="https://kavachiq.com/contact" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://kavachiq.com/contact" />
        <meta property="og:title" content="Contact KavachIQ — Get in Touch" />
        <meta property="og:description" content="Reach out for demos, support, or partnership inquiries about M365 data protection." />
        <meta property="og:image" content="https://kavachiq.com/og-contact.jpg" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:image" content="https://kavachiq.com/og-contact.jpg" />
        <meta name="twitter:title" content="Contact KavachIQ" />
      </Helmet>
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-card/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link to="/welcome" className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-teal-500" />
            <span className="font-bold text-foreground">KavachIQ</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <Link to="/welcome" className="hover:text-foreground">Home</Link>
            <Link to="/about" className="hover:text-foreground">About</Link>
            <Link to="/welcome#pricing" className="hover:text-foreground">Pricing</Link>
            <Link to="/contact" className="text-foreground font-medium">Contact</Link>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <a href={appUrl('/login')} className="text-sm text-muted-foreground hover:text-foreground">Sign In</a>
          </div>
        </div>
      </nav>

      <div className="pt-24 pb-16 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-3xl font-bold mb-3">Get in Touch</h1>
            <p className="text-muted-foreground">Questions about KavachIQ? We'd love to hear from you.</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Contact Form */}
            <div className="bg-card border border-border rounded-2xl p-6">
              <h2 className="text-lg font-semibold mb-4">Send a Message</h2>
              {submitted ? (
                <div className="text-center py-8">
                  <div className="w-12 h-12 bg-teal-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
                    <Send className="w-6 h-6 text-teal-400" />
                  </div>
                  <p className="text-foreground font-medium">Message sent!</p>
                  <p className="text-sm text-muted-foreground mt-1">We'll get back to you within 24 hours.</p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Name</label>
                    <input type="text" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                      className="w-full mt-1 px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-ring" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Email</label>
                    <input type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                      className="w-full mt-1 px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-ring" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Company</label>
                    <input type="text" value={form.company} onChange={e => setForm({ ...form, company: e.target.value })}
                      className="w-full mt-1 px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-ring" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Message</label>
                    <textarea required rows={4} value={form.message} onChange={e => setForm({ ...form, message: e.target.value })}
                      className="w-full mt-1 px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-ring resize-none" />
                  </div>
                  <button type="submit"
                    className="w-full py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 transition-colors flex items-center justify-center gap-2">
                    Send Message <ArrowRight className="w-4 h-4" />
                  </button>
                </form>
              )}
            </div>

            {/* Contact Info */}
            <div className="space-y-6">
              <div className="bg-card border border-border rounded-2xl p-6">
                <h2 className="text-lg font-semibold mb-4">Other Ways to Reach Us</h2>
                <div className="space-y-4">
                  <a href="mailto:hello@kavachiq.com" className="flex items-center gap-3 text-sm text-foreground hover:text-teal-400 transition-colors">
                    <div className="w-8 h-8 bg-teal-500/10 rounded-lg flex items-center justify-center"><Mail className="w-4 h-4 text-teal-400" /></div>
                    hello@kavachiq.com
                  </a>
                  <a href="https://github.com/gpatwa/m365-vault" target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-3 text-sm text-foreground hover:text-teal-400 transition-colors">
                    <div className="w-8 h-8 bg-muted rounded-lg flex items-center justify-center"><Github className="w-4 h-4 text-foreground" /></div>
                    GitHub — Open Source
                  </a>
                  <a href="https://linkedin.com/company/kavachiq" target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-3 text-sm text-foreground hover:text-teal-400 transition-colors">
                    <div className="w-8 h-8 bg-blue-500/10 rounded-lg flex items-center justify-center"><Linkedin className="w-4 h-4 text-blue-400" /></div>
                    LinkedIn
                  </a>
                </div>
              </div>

              <div className="bg-gradient-to-br from-teal-600 to-cyan-700 rounded-2xl p-6 text-white">
                <Calendar className="w-8 h-8 mb-3 text-teal-200" />
                <h3 className="text-lg font-semibold mb-2">Book a Demo</h3>
                <p className="text-sm text-teal-100 mb-4">See KavachIQ protect your M365 data in 10 minutes. Free, no commitment.</p>
                <a href={appUrl('/login?register=true')}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-white text-teal-700 rounded-lg font-medium text-sm hover:bg-teal-50 transition-colors">
                  Start Free Trial <ArrowRight className="w-4 h-4" />
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
