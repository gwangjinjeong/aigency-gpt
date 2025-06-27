import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import {
  MessageCircle,
  FileText,
  Search,
  Zap,
  ArrowRight,
  Globe,
  Users,
  Shield
} from 'lucide-react';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { t, language, setLanguage } = useLanguage();

  const handleStartChat = () => {
    navigate('/chat');
  };

  const toggleLanguage = () => {
    setLanguage(language === 'ko' ? 'en' : 'ko');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <MessageCircle className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">AI Assistant</span>
          </div>

          <div className="flex items-center space-x-4">
            <Button
              onClick={toggleLanguage}
              variant="outline"
              size="sm"
              className="flex items-center space-x-2"
            >
              <Globe className="w-4 h-4" />
              <span>{language === 'ko' ? '한국어' : 'English'}</span>
            </Button>

            <Button
              onClick={handleStartChat}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {t('landing.startChat')}
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6 leading-tight">
            {language === 'ko' ? '스마트한 AI와 함께하는' : 'Smart AI-Powered'}
            <br />
            <span className="text-blue-600">
              {language === 'ko' ? '문서 대화' : 'Document Chat'}
            </span>
          </h1>

          <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto leading-relaxed">
            {language === 'ko'
              ? 'PDF 문서를 업로드하고 AI와 대화하며 원하는 정보를 빠르게 찾아보세요. 복잡한 문서도 쉽게 이해할 수 있습니다.'
              : 'Upload PDF documents and chat with AI to quickly find the information you need. Make complex documents easy to understand.'
            }
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Button
              onClick={handleStartChat}
              size="lg"
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 text-lg"
            >
              <MessageCircle className="w-5 h-5 mr-2" />
              {language === 'ko' ? '지금 시작하기' : 'Start Now'}
            </Button>

            <Button
              variant="outline"
              size="lg"
              className="px-8 py-4 text-lg"
              onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
            >
              {language === 'ko' ? '기능 살펴보기' : 'Learn More'}
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            {language === 'ko' ? '주요 기능' : 'Key Features'}
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            {language === 'ko'
              ? 'AI 기반의 스마트한 문서 분석 도구로 업무 효율성을 높여보세요'
              : 'Boost your productivity with AI-powered smart document analysis tools'
            }
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {/* Feature 1 */}
          <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-6">
              <FileText className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              {language === 'ko' ? 'PDF 문서 분석' : 'PDF Document Analysis'}
            </h3>
            <p className="text-gray-600 leading-relaxed">
              {language === 'ko'
                ? 'PDF 파일을 업로드하면 AI가 자동으로 내용을 분석하고 구조화하여 쉽게 검색할 수 있게 합니다.'
                : 'Upload PDF files and AI automatically analyzes and structures content for easy searching.'
              }
            </p>
          </div>

          {/* Feature 2 */}
          <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-6">
              <Search className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              {language === 'ko' ? '스마트 검색' : 'Smart Search'}
            </h3>
            <p className="text-gray-600 leading-relaxed">
              {language === 'ko'
                ? '자연어로 질문하면 문서 내에서 관련 정보를 찾아 정확한 답변을 제공합니다.'
                : 'Ask questions in natural language and get accurate answers from relevant information in documents.'
              }
            </p>
          </div>

          {/* Feature 3 */}
          <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-6">
              <MessageCircle className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              {language === 'ko' ? '대화형 인터페이스' : 'Interactive Interface'}
            </h3>
            <p className="text-gray-600 leading-relaxed">
              {language === 'ko'
                ? '채팅하듯 편리하게 문서에 대해 질문하고 즉시 답변을 받을 수 있습니다.'
                : 'Ask questions about documents conversationally and get instant answers like chatting.'
              }
            </p>
          </div>

          {/* Feature 4 */}
          <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center mb-6">
              <Zap className="w-6 h-6 text-yellow-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              {language === 'ko' ? '빠른 처리' : 'Fast Processing'}
            </h3>
            <p className="text-gray-600 leading-relaxed">
              {language === 'ko'
                ? '최적화된 AI 엔진으로 대용량 문서도 빠르게 처리하고 분석합니다.'
                : 'Process and analyze even large documents quickly with optimized AI engine.'
              }
            </p>
          </div>

          {/* Feature 5 */}
          <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center mb-6">
              <Shield className="w-6 h-6 text-red-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              {language === 'ko' ? '보안 우선' : 'Security First'}
            </h3>
            <p className="text-gray-600 leading-relaxed">
              {language === 'ko'
                ? '업로드된 문서는 안전하게 처리되며 개인정보 보호를 최우선으로 합니다.'
                : 'Uploaded documents are processed securely with privacy protection as top priority.'
              }
            </p>
          </div>

          {/* Feature 6 */}
          <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
            <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-6">
              <Users className="w-6 h-6 text-indigo-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              {language === 'ko' ? '다중 언어 지원' : 'Multi-language Support'}
            </h3>
            <p className="text-gray-600 leading-relaxed">
              {language === 'ko'
                ? '한국어와 영어를 지원하며 다양한 언어로 작성된 문서를 처리할 수 있습니다.'
                : 'Supports Korean and English, and can process documents written in various languages.'
              }
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-blue-600 text-white py-20">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold mb-6">
            {language === 'ko' ? '지금 바로 시작해보세요!' : 'Get Started Now!'}
          </h2>
          <p className="text-xl mb-8 opacity-90 max-w-2xl mx-auto">
            {language === 'ko'
              ? 'AI와 함께하는 스마트한 문서 분석을 경험해보세요. 복잡한 설정 없이 바로 사용할 수 있습니다.'
              : 'Experience smart document analysis with AI. Start using immediately without complex setup.'
            }
          </p>

          <Button
            onClick={handleStartChat}
            size="lg"
            className="bg-white text-blue-600 hover:bg-gray-100 px-8 py-4 text-lg font-semibold"
          >
            <MessageCircle className="w-5 h-5 mr-2" />
            {language === 'ko' ? '무료로 시작하기' : 'Start Free'}
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <MessageCircle className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold">AI Assistant</span>
            </div>

            <p className="text-gray-400 text-center md:text-right">
              {language === 'ko'
                ? '© 2025 AI Assistant. 모든 권리 보유.'
                : '© 2025 AI Assistant. All rights reserved.'
              }
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;