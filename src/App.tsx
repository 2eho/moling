import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import BottomNav from './components/layout/BottomNav';
import HealthWarning from './components/HealthWarning';
import NotFound from './pages/NotFound';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'write' | 'library' | 'more'>('write');

  return (
    <>
      {/* 后端健康检查警告条 */}
      <HealthWarning />

      <Routes>
        {/* 首页 */}
        <Route
          path="/"
          element={
            <div style={{ padding: '20px', paddingBottom: '80px' }}>
              <h1>墨灵写作</h1>
              <p>当前标签: {activeTab}</p>
              
              <BottomNav
                activeTab={activeTab}
                onTabChange={setActiveTab}
                isEditorFullscreen={false}
              />
            </div>
          }
        />

        {/* 404 页面 - 捕获所有未匹配路由 */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
};

export default App;
