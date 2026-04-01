import { useState } from 'react';
import { MessageCircle, X, Send, ThumbsUp, Star } from 'lucide-react';
import { api } from '../api/client';

export default function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState<'rating' | 'details' | 'thanks'>('rating');
  const [rating, setRating] = useState<number>(0);
  const [category, setCategory] = useState('');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  const submit = async () => {
    setSending(true);
    try {
      await api.post('/audit/logs', {
        action: 'feedback.submitted',
        details: JSON.stringify({ rating, category, message }),
        severity: 'info',
        resource_type: 'feedback',
      });
    } catch {
      // Silent fail — feedback is best-effort
    }
    setSending(false);
    setStep('thanks');
    setTimeout(() => {
      setIsOpen(false);
      setStep('rating');
      setRating(0);
      setCategory('');
      setMessage('');
    }, 2000);
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg hover:shadow-xl transition-all group"
        title="Give feedback"
      >
        <MessageCircle className="w-5 h-5" />
        <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-40 w-80">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-3 flex items-center justify-between">
          <span className="text-white text-sm font-semibold">Share Feedback</span>
          <button onClick={() => setIsOpen(false)} className="text-white/70 hover:text-white"><X className="w-4 h-4" /></button>
        </div>

        <div className="p-5">
          {step === 'rating' && (
            <div>
              <p className="text-sm text-gray-700 font-medium mb-3">How's your experience with Shieldio?</p>
              <div className="flex justify-center gap-1 mb-4">
                {[1, 2, 3, 4, 5].map(n => (
                  <button key={n} onClick={() => setRating(n)} className="p-1 transition-transform hover:scale-110">
                    <Star className={`w-8 h-8 ${n <= rating ? 'text-amber-400 fill-amber-400' : 'text-gray-200'} transition-colors`} />
                  </button>
                ))}
              </div>
              {rating > 0 && (
                <div className="space-y-2">
                  <p className="text-xs text-gray-500">What area is this about?</p>
                  <div className="flex flex-wrap gap-1.5">
                    {['UI/Design', 'Performance', 'Features', 'Documentation', 'Pricing', 'Other'].map(cat => (
                      <button
                        key={cat}
                        onClick={() => { setCategory(cat); setStep('details'); }}
                        className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${category === cat ? 'bg-blue-500/10 border-blue-300 text-blue-400' : 'bg-gray-800/50 border-gray-200 text-gray-600 hover:border-gray-300'}`}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {step === 'details' && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="flex gap-0.5">
                  {[1, 2, 3, 4, 5].map(n => (
                    <Star key={n} className={`w-3.5 h-3.5 ${n <= rating ? 'text-amber-400 fill-amber-400' : 'text-gray-200'}`} />
                  ))}
                </div>
                <span className="text-xs text-gray-400">•</span>
                <span className="text-xs text-gray-500">{category}</span>
              </div>
              <textarea
                value={message}
                onChange={e => setMessage(e.target.value)}
                placeholder="Tell us more... What's working well? What could be better?"
                className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm resize-none h-24 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder:text-gray-300"
                autoFocus
              />
              <div className="flex justify-between items-center mt-3">
                <button onClick={() => setStep('rating')} className="text-xs text-gray-400 hover:text-gray-600">Back</button>
                <button
                  onClick={submit}
                  disabled={sending}
                  className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 flex items-center gap-1.5 disabled:opacity-50 transition-colors"
                >
                  {sending ? <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  Submit
                </button>
              </div>
            </div>
          )}

          {step === 'thanks' && (
            <div className="text-center py-4">
              <div className="w-12 h-12 bg-green-500/15 rounded-full flex items-center justify-center mx-auto mb-3">
                <ThumbsUp className="w-6 h-6 text-green-600" />
              </div>
              <p className="text-sm font-semibold text-gray-800">Thank you!</p>
              <p className="text-xs text-gray-500 mt-1">Your feedback helps us improve Shieldio.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
