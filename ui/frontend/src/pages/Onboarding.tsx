import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, ChevronLeft, Check, Loader2 } from 'lucide-react'
import api from '../api/client'
import StatusDot from '../components/common/StatusDot'
import MaskedField from '../components/common/MaskedField'

const API_KEYS = [
  { key: 'telegram_bot_token', label: 'Telegram Bot Token', required: true },
  { key: 'telegram_chat_id', label: 'Telegram Chat ID', required: true },
  { key: 'twelvedata', label: 'Twelve Data API Key', required: false },
  { key: 'finnhub', label: 'Finnhub API Key', required: false },
  { key: 'fred', label: 'FRED API Key', required: false },
  { key: 'newsapi', label: 'NewsAPI Key', required: false },
  { key: 'anthropic', label: 'Anthropic API Key (LLM)', required: false },
  { key: 'openai', label: 'OpenAI API Key (LLM)', required: false },
  { key: 'gemini', label: 'Gemini API Key (LLM)', required: false },
]

const STEPS = ['Welcome', 'API Keys', 'Test Telegram', 'Done']

export default function Onboarding() {
  const [step, setStep] = useState(0)
  const [keys, setKeys] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState<Record<string, boolean>>({})
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({})
  const [testing, setTesting] = useState<string | null>(null)
  const [telegramResult, setTelegramResult] = useState<{ success: boolean; message: string } | null>(null)
  const navigate = useNavigate()

  const saveKey = async (keyName: string) => {
    try {
      await api.post('/onboarding/api-key', { key: keyName, value: keys[keyName] || '' })
      setSaved(prev => ({ ...prev, [keyName]: true }))
    } catch {
      // ignore
    }
  }

  const testApi = async (apiName: string) => {
    setTesting(apiName)
    try {
      const res = await api.post(`/onboarding/test/${apiName}`)
      setTestResults(prev => ({ ...prev, [apiName]: res.data }))
    } catch (err: any) {
      setTestResults(prev => ({ ...prev, [apiName]: { success: false, message: 'Test failed' } }))
    } finally {
      setTesting(null)
    }
  }

  const testTelegram = async () => {
    setTesting('telegram')
    try {
      const res = await api.post('/onboarding/test-telegram')
      setTelegramResult(res.data)
    } catch {
      setTelegramResult({ success: false, message: 'Failed to send test message' })
    } finally {
      setTesting(null)
    }
  }

  return (
    <div className="min-h-screen bg-apple-gray-100 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full">
        {/* Progress */}
        <div className="flex items-center gap-2 mb-8 justify-center">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                i < step ? 'bg-apple-green text-white' :
                i === step ? 'bg-apple-blue text-white' :
                'bg-apple-gray-200 text-apple-gray-400'
              }`}>
                {i < step ? <Check size={14} /> : i + 1}
              </div>
              <span className={`text-xs hidden sm:inline ${i === step ? 'text-apple-gray-800 font-medium' : 'text-apple-gray-400'}`}>{s}</span>
              {i < STEPS.length - 1 && <div className="w-8 h-px bg-apple-gray-300" />}
            </div>
          ))}
        </div>

        <div className="card">
          {/* Step 0: Welcome */}
          {step === 0 && (
            <div className="text-center py-8">
              <h2 className="text-2xl font-semibold mb-4">Welcome to Market Digest</h2>
              <p className="text-apple-gray-500 max-w-md mx-auto mb-2">
                This wizard will help you configure your API keys, test connections,
                and run your first digest.
              </p>
              <p className="text-apple-gray-400 text-sm">
                At minimum, you need Telegram configured to receive digests.
                Data source and LLM keys are optional but recommended.
              </p>
            </div>
          )}

          {/* Step 1: API Keys */}
          {step === 1 && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Configure API Keys</h2>
              <div className="space-y-4">
                {API_KEYS.map(({ key, label, required }) => (
                  <div key={key}>
                    <div className="flex items-center gap-2 mb-1">
                      <label className="label !mb-0">{label}</label>
                      {required && <span className="text-apple-red text-[10px]">Required</span>}
                      {saved[key] && <StatusDot status="green" />}
                    </div>
                    <MaskedField
                      value={keys[key] || ''}
                      onChange={v => setKeys(prev => ({ ...prev, [key]: v }))}
                      placeholder={`Enter ${label}`}
                      onSave={() => saveKey(key)}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: Test Telegram */}
          {step === 2 && (
            <div className="text-center py-8">
              <h2 className="text-lg font-semibold mb-4">Test Telegram Connection</h2>
              <p className="text-apple-gray-500 mb-6">
                Send a test message to verify your Telegram bot is working.
              </p>
              <button
                onClick={testTelegram}
                disabled={testing === 'telegram'}
                className="btn-primary text-base px-8 py-3"
              >
                {testing === 'telegram' ? (
                  <span className="flex items-center gap-2">
                    <Loader2 size={16} className="animate-spin" /> Sending...
                  </span>
                ) : 'Send Test Message'}
              </button>
              {telegramResult && (
                <div className={`mt-4 p-3 rounded-lg ${telegramResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                  {telegramResult.message}
                </div>
              )}
            </div>
          )}

          {/* Step 3: Done */}
          {step === 3 && (
            <div className="text-center py-8">
              <div className="w-16 h-16 rounded-full bg-apple-green/10 flex items-center justify-center mx-auto mb-4">
                <Check size={32} className="text-apple-green" />
              </div>
              <h2 className="text-lg font-semibold mb-2">Setup Complete!</h2>
              <p className="text-apple-gray-500 mb-6">
                Your Market Digest Command Center is ready. Head to the dashboard
                to run your first digest.
              </p>
              <button onClick={() => navigate('/')} className="btn-primary text-base px-8 py-3">
                Go to Dashboard
              </button>
            </div>
          )}

          {/* Navigation */}
          {step < 3 && (
            <div className="flex justify-between mt-8 pt-4 border-t border-apple-gray-100">
              <button
                onClick={() => setStep(s => s - 1)}
                disabled={step === 0}
                className="btn-secondary flex items-center gap-1"
              >
                <ChevronLeft size={14} /> Back
              </button>
              <button
                onClick={() => setStep(s => s + 1)}
                className="btn-primary flex items-center gap-1"
              >
                {step === 2 ? 'Finish' : 'Next'} <ChevronRight size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
