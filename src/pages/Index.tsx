
import React, { useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import Header from '@/components/Layout/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { MessageCircle, Shield, FileText, Languages, Zap, Lock } from 'lucide-react';

const Index = () => {
  const { user } = useAuth();
  const { t } = useLanguage();

  // Redirect logged-in users to appropriate page
  useEffect(() => {
    if (user) {
      if (user.role === 'admin') {
        window.location.href = '/admin';
      } else {
        window.location.href = '/chat';
      }
    }
  }, [user]);

  const features = [
    {
      icon: MessageCircle,
      title: 'AI Chat Assistant',
      description: 'Get instant answers to loan-related questions with AI-powered responses',
    },
    {
      icon: FileText,
      title: 'Document Reference',
      description: 'Access relevant PDF pages and citations for every answer',
    },
    {
      icon: Languages,
      title: 'Bilingual Support',
      description: 'Available in both Korean and English languages',
    },
    {
      icon: Shield,
      title: 'Admin Controls',
      description: 'Secure document upload and management for administrators',
    },
    {
      icon: Zap,
      title: 'Vector Search',
      description: 'Fast and accurate document search using advanced AI technology',
    },
    {
      icon: Lock,
      title: 'Secure Access',
      description: 'Role-based authentication ensuring data security',
    },
  ];

  if (user) return null; // Will redirect via useEffect

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <Header />
      
      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Smart Banking
            <span className="text-blue-600"> Assistant</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            AI-powered loan consultation platform for banks and customers. 
            Get instant answers with document references in Korean and English.
          </p>
          <div className="flex justify-center space-x-4">
            <Button
              size="lg"
              onClick={() => window.location.href = '/login'}
              className="px-8 py-3 text-lg"
            >
              Get Started
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => window.location.href = '/chat'}
              className="px-8 py-3 text-lg"
            >
              Try Demo
            </Button>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-16">
          {features.map((feature, index) => (
            <Card key={index} className="hover:shadow-lg transition-shadow duration-300">
              <CardHeader>
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                  <feature.icon className="w-6 h-6 text-blue-600" />
                </div>
                <CardTitle className="text-xl">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-gray-600">
                  {feature.description}
                </CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Demo Section */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-2xl p-8 text-white text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Experience Smart Banking?</h2>
          <p className="text-blue-100 mb-6 text-lg">
            Join thousands of users who trust our AI-powered loan consultation platform
          </p>
          <div className="flex justify-center space-x-4">
            <Button
              size="lg"
              variant="secondary"
              onClick={() => window.location.href = '/login'}
              className="px-8 py-3"
            >
              Start Now
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
