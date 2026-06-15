import { useEffect, useState } from "react";
import {
  createAnalysisConfig,
  deleteAnalysisConfig,
  getAnalysisConfigs,
} from "../api/analysisConfigs";
import type { AnalysisModules, UserAnalysisConfig } from "../types/db";

const emptyModules: AnalysisModules = {
  audio: true,
  text: true,
  face: true,
  report: true,
};

const AnalysisConfigurator = () => {
  const [configs, setConfigs] = useState<UserAnalysisConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [modules, setModules] = useState<AnalysisModules>(emptyModules);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await getAnalysisConfigs();
      setConfigs(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить конфигурации");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onCreate = async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    try {
      await createAnalysisConfig({
        name: trimmed,
        modulesJson: {
          audio: modules.audio ?? false,
          text: modules.text ?? false,
          face: modules.face ?? false,
          report: modules.report ?? false,
        },
      });
      setName("");
      setModules(emptyModules);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать конфигурацию");
    }
  };

  const onDelete = async (id: number) => {
    try {
      await deleteAnalysisConfig(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось удалить конфигурацию");
    }
  };

  const toggle = (key: keyof AnalysisModules) => {
    setModules((prev) => ({ ...prev, [key]: !(prev[key] ?? false) }));
  };

  return (
    <div className="config-section">
      <h2>Конфигуратор анализа</h2>
      <p className="config-help">
        Создайте конфигурации модулей и выбирайте их при создании сессии.
      </p>
      {error && <p className="warning">{error}</p>}

      <div className="summary-box" style={{ marginBottom: 16 }}>
        <h3>Новая конфигурация</h3>
        <div className="form-row">
          <div className="form-group">
            <label>Название</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: Интервью (только текст+face)"
            />
          </div>
        </div>
        <div className="emotion-selector">
          {(["audio", "text", "face", "report"] as Array<keyof AnalysisModules>).map((k) => (
            <label key={k}>
              <input
                type="checkbox"
                checked={Boolean(modules[k])}
                onChange={() => toggle(k)}
              />
              {k}
            </label>
          ))}
        </div>
        <div style={{ marginTop: 12 }}>
          <button className="primary-btn" type="button" onClick={onCreate}>
            Сохранить конфигурацию
          </button>
        </div>
      </div>

      <div className="summary-box">
        <h3>Мои конфигурации</h3>
        {loading ? (
          <p>Загрузка...</p>
        ) : configs.length === 0 ? (
          <p className="warning">У вас нет ни 1 конфигурации, составьте её.</p>
        ) : (
          <table className="participants-table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Модули</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {configs.map((cfg) => (
                <tr key={cfg.analysisConfigId}>
                  <td>{cfg.name}</td>
                  <td>
                    {Object.entries(cfg.modulesJson ?? {})
                      .filter(([, on]) => Boolean(on))
                      .map(([k]) => k)
                      .join(", ") || "все выключены"}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="action-btn small"
                      onClick={() => onDelete(cfg.analysisConfigId)}
                    >
                      Удалить
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default AnalysisConfigurator;

