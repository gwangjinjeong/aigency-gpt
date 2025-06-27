import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// 디버깅용 로그
console.log('main.tsx가 실행되었습니다.');

const rootElement = document.getElementById('root');
console.log('root 엘리먼트:', rootElement);

if (rootElement) {
  const root = createRoot(rootElement);
  console.log('React root 생성됨');

  root.render(
    <StrictMode>
      <App />
    </StrictMode>
  );
  console.log('App 렌더링 완료');
} else {
  console.error('root 엘리먼트를 찾을 수 없습니다!');
}