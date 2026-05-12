import React, { useState } from 'react';

interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (description: string) => void;
  title: string;
  subtitle?: string;
}

const ReportModal: React.FC<ReportModalProps> = ({ isOpen, onClose, onSubmit, title, subtitle }) => {
  const [description, setDescription] = useState('');

  if (!isOpen) return null;

  const handleSubmit = () => {
    onSubmit(description || '使用者未提供詳細描述');
    setDescription('');
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{title}</h2>
          {subtitle && <p className="modal-subtitle">{subtitle}</p>}
        </div>
        <div className="modal-body">
          <textarea
            className="modal-input"
            placeholder="請輸入錯誤描述（例如：回答不正確、格式錯誤等）..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            autoFocus
          />
        </div>
        <div className="modal-footer">
          <button className="modal-btn modal-btn-cancel" onClick={onClose}>
            取消
          </button>
          <button className="modal-btn modal-btn-submit" onClick={handleSubmit}>
            提交回報
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReportModal;
