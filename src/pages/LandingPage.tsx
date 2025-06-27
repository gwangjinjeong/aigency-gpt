import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  FileText,
  MessageCircle,
  Zap,
  Search,
  Highlighter,
  MapPin,
  Upload,
  Brain,
  Target,
  Users,
  ArrowRight,
  CheckCircle,
  Sparkles
} from 'lucide-react';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { t } = useLanguage();

  const handleGetStarted = () => {
    if (user) {
      navigate('/chat');
    } else {
      navigate('/login');
    }
  };

  const handleAdminAccess = () => {
    if (user?.role === 'admin') {
      navigate('/admin');
    } else {
      navigate('/login');
    }
  };

  const features = [
    {
      icon: <Brain className="w-8 h-8 text-blue-600" />,
      title: "AI 기반 문서 분석",
      description: "GPT-4와 RAG 기술로 PDF 문서를 정확히 이해하고 답변합니다"
    },
    {
      icon: <MapPin className="w-8 h-8 text-green-600" />,
      title: "자동 페이지 이동",
      description: "답변과 함께 관련 PDF 페이지로 자동 이동하여 출처를 확인할 수 있습니다"
    },
    {
      icon: <Highlighter className="w-8 h-8 text-yellow-600" />,
      title: "텍스트 하이라이트",
      description: "관련 텍스트를 자동으로 하이라이트하여 쉽게 찾을 수 있습니다"
    },
    {
      icon: <Search className="w-8 h-8 text-purple-600" />,
      title: "실시간 검색",
      description: "PDF 내 모든 텍스트를 실시간으로 검색하고 위치를 찾아줍니다"
    },
    {
      icon: <Upload className="w-8 h-8 text-indigo-600" />,
      title: "쉬운 업로드",
      description: "PDF 파일을 드래그 앤 드롭으로 업로드하면 자동으로 분석됩니다"
    },
    {
      icon: <Zap className="w-8 h-8 text-orange-600" />,
      title: "빠른 응답",
      description: "벡터 데이터베이스로 수초 내에 정확한 답변을 제공합니다"
    }
  ];

  const stats = [
    { label: "처리 속도", value: "< 3초", icon: <Zap className="w-5 h-5" /> },
    { label: "정확도", value: "95%+", icon: <Target className="w-5 h-5" /> },
    { label: "지원 언어", value: "한/영", icon: <FileText className="w-5 h-5" /> },
    { label: "동시 사용자", value: "100+", icon: <Users className="w-5 h-5" /> }
  ];

  const useCases = [
    "📋 업무 매뉴얼 및 가이드라인 검색",
    "📄 계약서 및 법률 문서 분석",
    "📚 연구 논문 및 보고서 질의응답",
    "🏦 금융 상품 설명서 안내",
    "🏥 의료 진료 가이드라인 참조",
    "🎓 교육 자료 및 교재 학습"
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* 헤더 */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                DocuChat AI
              </span>
            </div>

            <div className="flex items-center space-x-4">
              {user ? (
                <div className="flex items-center space-x-3">
                  <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                    {user.name}
                  </Badge>
                  <Button onClick={() => navigate('/chat')} className="bg-blue-600 hover:bg-blue-700">
                    채팅하기
                  </Button>
                  {user.role === 'admin' && (
                    <Button onClick={handleAdminAccess} variant="outline">
                      관리자
                    </Button>
                  )}
                </div>
              ) : (
                <div className="flex items-center space-x-3">
                  <Button onClick={() => navigate('/login')} variant="outline">
                    로그인
                  </Button>
                  <Button onClick={handleGetStarted} className="bg-blue-600 hover:bg-blue-700">
                    시작하기
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* 히어로 섹션 */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <div className="flex justify-center mb-6">
            <Badge className="bg-blue-100 text-blue-800 border-blue-200 px-4 py-2">
              <Sparkles className="w-4 h-4 mr-2" />
              AI 기반 문서 질의응답 시스템
            </Badge>
          </div>

          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            PDF 문서와
            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              {" "}대화하세요
            </span>
          </h1>

          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto leading-relaxed">
            RAG와 벡터 검색 기술로 PDF 문서의 내용을 정확히 이해하고,
            관련 페이지로 자동 이동하며 하이라이트까지 제공하는 혁신적인 AI 서비스입니다.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <Button
              onClick={handleGetStarted}
              size="lg"
              className="bg-blue-600 hover:bg-blue-700 text-lg px-8 py-3"
            >
              <MessageCircle className="w-5 h-5 mr-2" />
              무료로 시작하기
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>

            <Button
              onClick={() => navigate('/demo')}
              size="lg"
              variant="outline"
              className="text-lg px-8 py-3 border-blue-200 hover:bg-blue-50"
            >
              <FileText className="w-5 h-5 mr-2" />
              데모 체험하기
            </Button>
          </div>

          {/* 통계 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
            {stats.map((stat, index) => (
              <Card key={index} className="text-center border-0 shadow-sm bg-white/60 backdrop-blur-sm">
                <CardContent className="p-6">
                  <div className="flex justify-center mb-2 text-blue-600">
                    {stat.icon}
                  </div>
                  <div className="text-2xl font-bold text-gray-900 mb-1">{stat.value}</div>
                  <div className="text-sm text-gray-600">{stat.label}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 주요 기능 */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              왜 DocuChat AI인가요?
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              단순한 키워드 검색을 넘어, AI가 문서를 이해하고 정확한 답변을 제공합니다
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <Card key={index} className="hover:shadow-lg transition-all duration-300 border-0 shadow-sm">
                <CardHeader className="text-center">
                  <div className="flex justify-center mb-4">
                    {feature.icon}
                  </div>
                  <CardTitle className="text-xl">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-center text-gray-600 leading-relaxed">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 사용 사례 */}
      <section className="py-20 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              다양한 분야에서 활용하세요
            </h2>
            <p className="text-xl text-gray-600">
              업무 효율성을 높이는 실제 사용 사례들
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {useCases.map((useCase, index) => (
              <div key={index} className="flex items-center space-x-3 bg-white p-4 rounded-lg shadow-sm">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                <span className="text-gray-700">{useCase}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA 섹션 */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-indigo-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold text-white mb-6">
            지금 바로 시작해보세요
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            PDF 업로드부터 AI 답변까지, 3분이면 충분합니다
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button
              onClick={handleGetStarted}
              size="lg"
              className="bg-white text-blue-600 hover:bg-gray-100 text-lg px-8 py-3"
            >
              <Upload className="w-5 h-5 mr-2" />
              PDF 업로드하고 시작하기
            </Button>

            {!user && (
              <Button
                onClick={() => navigate('/login')}
                size="lg"
                variant="outline"
                className="border-white text-white hover:bg-white hover:text-blue-600 text-lg px-8 py-3"
              >
                로그인하기
              </Button>
            )}
          </div>
        </div>
      </section>

      {/* 푸터 */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="col-span-2">
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <span className="text-2xl font-bold">DocuChat AI</span>
              </div>
              <p className="text-gray-400 max-w-md">
                AI 기술로 문서와 대화하는 새로운 경험을 제공합니다.
                더 스마트한 업무 환경을 만들어보세요.
              </p>
            </div>

            <div>
              <h3 className="font-semibold mb-4">서비스</h3>
              <ul className="space-y-2 text-gray-400">
                <li><a href="/chat" className="hover:text-white">AI 채팅</a></li>
                <li><a href="/admin" className="hover:text-white">문서 관리</a></li>
                <li><a href="/demo" className="hover:text-white">데모</a></li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold mb-4">지원</h3>
              <ul className="space-y-2 text-gray-400">
                <li><a href="/help" className="hover:text-white">도움말</a></li>
                <li><a href="/contact" className="hover:text-white">문의하기</a></li>
                <li><a href="/api" className="hover:text-white">API 문서</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2024 DocuChat AI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;