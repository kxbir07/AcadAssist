import { CheckCircle2, Info, X, XCircle } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function ToastContainer() {
  const { toasts, dismissToast } = useApp();
  return <div className="toast-stack" aria-live="polite">
    {toasts.map(t => <div className={`app-toast ${t.type}`} key={t.id}>
      {t.type === 'success' ? <CheckCircle2 size={17}/> : t.type === 'error' ? <XCircle size={17}/> : <Info size={17}/>}<span>{t.message}</span>
      <button onClick={() => dismissToast(t.id)} aria-label="Dismiss notification"><X size={14}/></button>
    </div>)}
  </div>;
}
