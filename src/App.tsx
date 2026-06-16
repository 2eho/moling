import React, { useState } from 'react';
import BottomNav from './components/layout/BottomNav';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'write' | 'library' | 'more'>('write');

  return (
    <div style={{ padding: '20px', paddingBottom: '80px' }}>
      <h1>墨灵写作</h1>
      <p>当前标签: {activeTab}</p>
      
      <BottomNav
        activeTab={activeTab}
        onTabChange={setActiveTab}
        isEditorFullscreen={false}
      />
    </div>
  );
};

export default App;
