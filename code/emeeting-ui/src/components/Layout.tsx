import Sidebar from "./Sidebar";
import { useUIStore } from "../store/uiStore";

const Layout = ({ children }: { children: React.ReactNode }) => {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);

  return (
    <div className={`app-shell ${sidebarOpen ? "" : "app-shell--sidebar-collapsed"}`}>
      <Sidebar />
      {!sidebarOpen && (
        <button
          type="button"
          className="sidebar-expand-fab"
          onClick={() => useUIStore.getState().setSidebarOpen(true)}
          title="Показать меню"
          aria-label="Показать меню"
        >
          ☰
        </button>
      )}
      <div className="app-content">
        <main>{children}</main>
        <footer>© 2026 EMeeting. Все права защищены.</footer>
      </div>
    </div>
  );
};

export default Layout;
