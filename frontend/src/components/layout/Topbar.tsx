import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Search, Bell, Menu, Sun, Moon, CheckCheck } from 'lucide-react';
import { useApp } from '../../context/AppContext';
export default function Topbar(){
  const navigate=useNavigate();
  const location=useLocation();
  const {user,setSidebarOpen,settings,updateSetting,notifications,markNotificationsRead,markNotificationRead}=useApp();
  const queryParam = new URLSearchParams(location.search).get('q') || '';
  const [searchVal,setSearchVal]=useState(queryParam);
  const [prevQuery,setPrevQuery]=useState(queryParam);
  if (queryParam !== prevQuery) {
    setPrevQuery(queryParam);
    setSearchVal(queryParam);
  }
  const [open,setOpen]=useState(false);
  const unread=notifications.filter(n=>!n.read).length;

  const submit=(e:FormEvent)=>{
    e.preventDefault();
    const value=searchVal.trim();
    if(value)navigate(`/knowledge?q=${encodeURIComponent(value)}`);
  };

  const toggle=()=>updateSetting('theme',settings.theme==='dark'?'light':'dark');

  return (
    <header className="topbar">
      <button className="topbar-icon-btn mobile-menu" onClick={()=>setSidebarOpen(true)} aria-label="Open navigation">
        <Menu size={18}/>
      </button>
      <form onSubmit={submit} className="topbar-search">
        <Search size={16}/>
        <input value={searchVal} onChange={e=>setSearchVal(e.target.value)} placeholder="Search courses, notes, topics..."/>
      </form>
      <button className="topbar-icon-btn theme-btn" onClick={toggle} aria-label="Toggle theme">
        {settings.theme==='dark'?<Moon size={16}/>:<Sun size={16}/>}
      </button>
      <div className="relative">
        <button className="topbar-icon-btn" onClick={()=>setOpen(v=>!v)} aria-label="Notifications">
          <Bell size={18}/>
          {unread>0&&<span className="notification-count">{unread}</span>}
        </button>
        {open&&(
          <div className="notification-panel">
            <div className="notification-head">
              <strong>Notifications</strong>
              <button onClick={markNotificationsRead}><CheckCheck size={14}/>Mark all read</button>
            </div>
            {notifications.length?notifications.map(n=>(
              <button
                key={n.id}
                className={`notification-item ${n.read?'read':''}`}
                onClick={()=>{
                  markNotificationRead(n.id);
                  setOpen(false);
                  if(n.link) navigate(n.link);
                }}
              >
                <span className={`notification-dot ${n.type}`}/>
                <span>
                  <b>{n.title}</b>
                  <small>{n.message}</small>
                </span>
              </button>
            )):<div className="empty-inline">No notifications.</div>}
          </div>
        )}
      </div>
      <Link to="/profile" className="topbar-avatar-pill">
        <div className="avatar-fallback">{user.name.slice(0,1).toUpperCase()}</div>
        <div>
          <span className="greeting">
            {new Date().getHours()<12?'Good morning,':new Date().getHours()<18?'Good afternoon,':'Good evening,'}
          </span>
          <strong>{user.name}</strong>
        </div>
      </Link>
    </header>
  );
}
