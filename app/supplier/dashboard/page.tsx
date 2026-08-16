'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ApiError, apiGet, apiPatch, apiPost } from '@/lib/apiClient';

type Profile = {
  user_id: string;
  geography: string | null;
  land_size_hectares: number | null;
  crop_or_livestock_type: string | null;
  ownership_status: string | null;
  payout_details_masked: string | null;
  is_complete: boolean;
  completion_percentage: number;
};

type Project = {
  id: string;
  supplier_id: string;
  title: string;
  description: string | null;
  methodology: string;
  geography: string;
  baseline: string | null;
  expected_volume: number | null;
  status: string;
  review_reason: string | null;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
};

type DocumentItem = {
  id: string;
  project_id: string;
  doc_type: string;
  filename: string;
  storage_uri: string;
  checksum: string;
  uploaded_at: string;
};

type FarmFormState = {
  geography: string;
  land_size_hectares: string;
  crop_or_livestock_type: string;
  ownership_status: string;
  payout_details: string;
};

type ProjectFormState = {
  title: string;
  description: string;
  methodology: string;
  geography: string;
  baseline: string;
  expected_volume: string;
};

const EMPTY_FARM_FORM: FarmFormState = {
  geography: '',
  land_size_hectares: '',
  crop_or_livestock_type: '',
  ownership_status: '',
  payout_details: '',
};

const EMPTY_PROJECT_FORM: ProjectFormState = {
  title: '',
  description: '',
  methodology: '',
  geography: '',
  baseline: '',
  expected_volume: '',
};

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  submitted: 'bg-amber-100 text-amber-700',
  in_review: 'bg-blue-100 text-blue-700',
  needs_info: 'bg-orange-100 text-orange-700',
  approved: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
};

export default function SupplierDashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [farmForm, setFarmForm] = useState<FarmFormState>(EMPTY_FARM_FORM);
  const [projectForm, setProjectForm] = useState<ProjectFormState>(EMPTY_PROJECT_FORM);
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [documentType, setDocumentType] = useState('registry_evidence');
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const applyProfile = useCallback((p: Profile) => {
    setProfile(p);
    setFarmForm({
      geography: p.geography ?? '',
      land_size_hectares: p.land_size_hectares?.toString() ?? '',
      crop_or_livestock_type: p.crop_or_livestock_type ?? '',
      ownership_status: p.ownership_status ?? '',
      payout_details: '',
    });
  }, []);

  const loadProjects = useCallback(async () => {
    const data = await apiGet<Project[]>('/projects');
    setProjects(data);
    if (data.length > 0 && !selectedProject) {
      setSelectedProject(data[0]);
      await loadProjectDocuments(data[0].id);
    }
  }, [selectedProject]);

  const loadProjectDocuments = useCallback(async (projectId: string) => {
    try {
      const data = await apiGet<DocumentItem[]>(`/projects/${projectId}/documents`);
      setDocuments(data);
    } catch {
      setDocuments([]);
    }
  }, []);

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      router.replace('/login');
      return;
    }

    const loadDashboard = async () => {
      try {
        const profileData = await apiGet<Profile>('/supplier/profile');
        applyProfile(profileData);
        const projectData = await apiGet<Project[]>('/projects');
        setProjects(projectData);
        if (projectData[0]) {
          setSelectedProject(projectData[0]);
          await loadProjectDocuments(projectData[0].id);
        }
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          router.replace('/login');
          return;
        }
        if (!(e instanceof ApiError && e.status === 404)) {
          setError(e instanceof ApiError ? e.message : 'Could not load your dashboard');
        }
      } finally {
        setLoading(false);
      }
    };

    void loadDashboard();
  }, [applyProfile, loadProjectDocuments, router]);

  async function handleProfileSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setNotice('');
    setSaving(true);

    const payload: Record<string, string | number> = {};
    if (farmForm.geography) payload.geography = farmForm.geography;
    if (farmForm.land_size_hectares) payload.land_size_hectares = Number(farmForm.land_size_hectares);
    if (farmForm.crop_or_livestock_type) payload.crop_or_livestock_type = farmForm.crop_or_livestock_type;
    if (farmForm.ownership_status) payload.ownership_status = farmForm.ownership_status;
    if (farmForm.payout_details) payload.payout_details = farmForm.payout_details;

    try {
      const updated = await apiPost<Profile>('/supplier/profile', payload);
      applyProfile(updated);
      setNotice('Profile saved.');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Network error – please try again');
    } finally {
      setSaving(false);
    }
  }

  async function handleProjectSave(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setNotice('');
    setSaving(true);

    const payload: Record<string, string | number> = {};
    if (projectForm.title.trim()) payload.title = projectForm.title.trim();
    if (projectForm.description.trim()) payload.description = projectForm.description.trim();
    if (projectForm.methodology.trim()) payload.methodology = projectForm.methodology.trim();
    if (projectForm.geography.trim()) payload.geography = projectForm.geography.trim();
    if (projectForm.baseline.trim()) payload.baseline = projectForm.baseline.trim();
    if (projectForm.expected_volume.trim()) payload.expected_volume = Number(projectForm.expected_volume);

    try {
      if (editingProjectId) {
        const updated = await apiPatch<Project>(`/projects/${editingProjectId}`, payload);
        setSelectedProject(updated);
        setNotice('Project updated.');
        await loadProjects();
      } else {
        const created = await apiPost<Project>('/projects', payload);
        setSelectedProject(created);
        setEditingProjectId(null);
        setNotice('Project created in draft state.');
        await loadProjects();
      }
      setProjectForm(EMPTY_PROJECT_FORM);
      setEditingProjectId(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not save project');
    } finally {
      setSaving(false);
    }
  }

  async function handleSelectProject(projectId: string) {
    const project = projects.find((item) => item.id === projectId);
    if (!project) return;
    setSelectedProject(project);
    setEditingProjectId(projectId);
    setProjectForm({
      title: project.title,
      description: project.description ?? '',
      methodology: project.methodology,
      geography: project.geography,
      baseline: project.baseline ?? '',
      expected_volume: project.expected_volume?.toString() ?? '',
    });
    await loadProjectDocuments(projectId);
  }

  async function handleSubmitProject(projectId: string) {
    try {
      setSubmitting(true);
      setError('');
      setNotice('');
      const updated = await apiPost<Project>(`/projects/${projectId}/submit`, {});
      setSelectedProject(updated);
      await loadProjects();
      setNotice('Project submitted for review.');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not submit project');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResubmitProject(projectId: string) {
    try {
      setSubmitting(true);
      setError('');
      setNotice('');
      const updated = await apiPost<Project>(`/projects/${projectId}/resubmit`, {});
      setSelectedProject(updated);
      await loadProjects();
      setNotice('Project resubmitted.');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not resubmit project');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUploadDocument(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProject || !documentFile) {
      setError('Choose a file before uploading.');
      return;
    }

    setUploading(true);
    setError('');
    setNotice('');

    const formData = new FormData();
    formData.append('doc_type', documentType);
    formData.append('file', documentFile);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/v1/projects/${selectedProject.id}/documents`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      const json = await response.json().catch(() => null);
      if (!response.ok) {
        throw new ApiError(
          typeof json?.detail === 'string' ? json.detail : 'Could not upload document',
          response.status,
        );
      }

      setDocumentFile(null);
      setNotice('Document uploaded successfully.');
      await loadProjectDocuments(selectedProject.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  function handleLogout() {
    apiPost('/auth/logout', {}).catch(() => undefined);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    router.replace('/login');
  }

  function updateFarm(field: keyof FarmFormState, value: string) {
    setFarmForm((prev) => ({ ...prev, [field]: value }));
  }

  function updateProject(field: keyof ProjectFormState, value: string) {
    setProjectForm((prev) => ({ ...prev, [field]: value }));
  }

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-green-50">
        <p className="text-green-800">Loading your dashboard…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-green-50 p-4">
      <div className="mx-auto w-full max-w-6xl">
        <header className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-green-800">Farmer Dashboard</h1>
          <button
            onClick={handleLogout}
            className="text-sm text-green-800 underline hover:text-green-900"
          >
            Log out
          </button>
        </header>

        <div className="grid gap-6 xl:grid-cols-[1.1fr_2fr]">
          <div className="space-y-6">
            <section className="bg-white rounded-2xl shadow-md p-6">
              <div className="flex items-center justify-between mb-2 text-sm font-medium text-gray-700">
                <span>Profile completion</span>
                <span>{profile?.completion_percentage ?? 0}%</span>
              </div>
              <div className="h-2 w-full rounded-full bg-gray-200">
                <div
                  className="h-2 rounded-full bg-green-600 transition-all"
                  style={{ width: `${profile?.completion_percentage ?? 0}%` }}
                />
              </div>
              {profile?.is_complete ? (
                <p className="mt-3 text-sm text-green-700">Your profile is complete.</p>
              ) : (
                <p className="mt-3 text-sm text-gray-600">
                  Complete every field to finish onboarding. Partial saves are kept.
                </p>
              )}

              <form onSubmit={handleProfileSubmit} className="mt-6 flex flex-col gap-4">
                <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                  Geography
                  <input
                    type="text"
                    value={farmForm.geography}
                    onChange={(e) => updateFarm('geography', e.target.value)}
                    className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Punjab, India"
                  />
                </label>

                <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                  Land size (hectares)
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={farmForm.land_size_hectares}
                    onChange={(e) => updateFarm('land_size_hectares', e.target.value)}
                    className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="12.5"
                  />
                </label>

                <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                  Crop / livestock type
                  <input
                    type="text"
                    value={farmForm.crop_or_livestock_type}
                    onChange={(e) => updateFarm('crop_or_livestock_type', e.target.value)}
                    className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Rice"
                  />
                </label>

                <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                  Ownership status
                  <select
                    value={farmForm.ownership_status}
                    onChange={(e) => updateFarm('ownership_status', e.target.value)}
                    className="border rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    <option value="">Select…</option>
                    <option value="owned">Owned</option>
                    <option value="leased">Leased</option>
                    <option value="cooperative">Cooperative</option>
                  </select>
                </label>

                <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                  Payout details
                  <input
                    type="text"
                    value={farmForm.payout_details}
                    onChange={(e) => updateFarm('payout_details', e.target.value)}
                    className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder={profile?.payout_details_masked ?? 'Bank account / UPI'}
                  />
                  {profile?.payout_details_masked && (
                    <span className="text-xs font-normal text-gray-500">
                      Saved: {profile.payout_details_masked} – leave blank to keep unchanged.
                    </span>
                  )}
                </label>

                <button
                  type="submit"
                  disabled={saving}
                  className="bg-green-700 text-white py-2 rounded-lg hover:bg-green-800 font-medium disabled:opacity-50"
                >
                  {saving ? 'Saving…' : 'Save profile'}
                </button>
              </form>
            </section>

            <section className="bg-white rounded-2xl shadow-md p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-green-800">Projects</h2>
                <button
                  type="button"
                  onClick={() => {
                    setEditingProjectId(null);
                    setProjectForm(EMPTY_PROJECT_FORM);
                    setSelectedProject(null);
                  }}
                  className="text-sm text-green-700 underline"
                >
                  New draft
                </button>
              </div>

              <div className="space-y-3">
                {projects.length === 0 ? (
                  <p className="text-sm text-gray-600">No projects yet. Create your first draft.</p>
                ) : (
                  projects.map((project) => (
                    <button
                      key={project.id}
                      type="button"
                      onClick={() => void handleSelectProject(project.id)}
                      className={`w-full rounded-xl border p-3 text-left transition ${
                        selectedProject?.id === project.id
                          ? 'border-green-600 bg-green-50'
                          : 'border-gray-200 bg-white hover:border-green-200'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold text-gray-800">{project.title}</p>
                          <p className="text-xs text-gray-500">{project.geography}</p>
                        </div>
                        <span
                          className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${STATUS_STYLES[project.status] ?? 'bg-gray-100 text-gray-700'}`}
                        >
                          {project.status.replace('_', ' ')}
                        </span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </section>
          </div>

          <div className="space-y-6">
            {(error || notice) && (
              <div className="rounded-xl border p-3 text-sm">
                {error && <p className="text-red-600">{error}</p>}
                {notice && <p className="text-green-700">{notice}</p>}
              </div>
            )}

            <section className="bg-white rounded-2xl shadow-md p-6">
              <h2 className="text-lg font-semibold text-green-800 mb-4">
                {selectedProject ? 'Project details' : 'Create project'}
              </h2>

              <form onSubmit={handleProjectSave} className="flex flex-col gap-4">
                <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                  Title
                  <input
                    type="text"
                    value={projectForm.title}
                    onChange={(e) => updateProject('title', e.target.value)}
                    className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Rice Field Carbon Sequestration"
                    required={!selectedProject}
                  />
                </label>

                <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                  Description
                  <textarea
                    value={projectForm.description}
                    onChange={(e) => updateProject('description', e.target.value)}
                    className="border rounded-lg px-3 py-2 min-h-24 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Describe the project, soil and farming changes, and expected impact."
                  />
                </label>

                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                    Methodology
                    <input
                      type="text"
                      value={projectForm.methodology}
                      onChange={(e) => updateProject('methodology', e.target.value)}
                      className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                      placeholder="VM0015"
                      required={!selectedProject}
                    />
                  </label>

                  <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                    Geography
                    <input
                      type="text"
                      value={projectForm.geography}
                      onChange={(e) => updateProject('geography', e.target.value)}
                      className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                      placeholder="Punjab, India"
                      required={!selectedProject}
                    />
                  </label>
                </div>

                <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                  Baseline
                  <textarea
                    value={projectForm.baseline}
                    onChange={(e) => updateProject('baseline', e.target.value)}
                    className="border rounded-lg px-3 py-2 min-h-20 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Business-as-usual emissions or land practice baseline"
                  />
                </label>

                <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                  Expected volume (tCO₂e)
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={projectForm.expected_volume}
                    onChange={(e) => updateProject('expected_volume', e.target.value)}
                    className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="1500"
                  />
                </label>

                <div className="flex flex-wrap gap-3">
                  <button
                    type="submit"
                    disabled={saving}
                    className="bg-green-700 text-white px-4 py-2 rounded-lg hover:bg-green-800 font-medium disabled:opacity-50"
                  >
                    {saving ? 'Saving…' : editingProjectId ? 'Update project' : 'Create project'}
                  </button>

                  {selectedProject && (
                    <>
                      {selectedProject.status === 'draft' && (
                        <button
                          type="button"
                          onClick={() => void handleSubmitProject(selectedProject.id)}
                          disabled={submitting}
                          className="bg-amber-600 text-white px-4 py-2 rounded-lg hover:bg-amber-700 font-medium disabled:opacity-50"
                        >
                          {submitting ? 'Submitting…' : 'Submit for review'}
                        </button>
                      )}

                      {selectedProject.status === 'needs_info' && (
                        <button
                          type="button"
                          onClick={() => void handleResubmitProject(selectedProject.id)}
                          disabled={submitting}
                          className="bg-orange-600 text-white px-4 py-2 rounded-lg hover:bg-orange-700 font-medium disabled:opacity-50"
                        >
                          {submitting ? 'Resubmitting…' : 'Resubmit'}
                        </button>
                      )}
                    </>
                  )}
                </div>
              </form>
            </section>

            {selectedProject && (
              <section className="bg-white rounded-2xl shadow-md p-6">
                <h2 className="text-lg font-semibold text-green-800 mb-4">Project status</h2>
                <div className="space-y-3 text-sm text-gray-700">
                  <div className="flex items-center justify-between">
                    <span>Status</span>
                    <span
                      className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${STATUS_STYLES[selectedProject.status] ?? 'bg-gray-100 text-gray-700'}`}
                    >
                      {selectedProject.status.replace('_', ' ')}
                    </span>
                  </div>
                  <p>
                    <strong>Created:</strong> {new Date(selectedProject.created_at).toLocaleString()}
                  </p>
                  <p>
                    <strong>Updated:</strong> {new Date(selectedProject.updated_at).toLocaleString()}
                  </p>
                  {selectedProject.submitted_at && (
                    <p>
                      <strong>Submitted:</strong> {new Date(selectedProject.submitted_at).toLocaleString()}
                    </p>
                  )}
                  {selectedProject.review_reason && (
                    <p>
                      <strong>Review reason:</strong> {selectedProject.review_reason}
                    </p>
                  )}
                </div>

                <form onSubmit={handleUploadDocument} className="mt-6 border-t pt-5">
                  <h3 className="text-md font-semibold text-green-800 mb-3">Upload documents</h3>
                  <div className="flex flex-col gap-3">
                    <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                      Document type
                      <select
                        value={documentType}
                        onChange={(e) => setDocumentType(e.target.value)}
                        className="border rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
                      >
                        <option value="registry_evidence">Registry evidence</option>
                        <option value="mrv_record">MRV record</option>
                        <option value="land_ownership_proof">Land ownership proof</option>
                        <option value="other">Other</option>
                      </select>
                    </label>

                    <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
                      File
                      <input
                        type="file"
                        onChange={(e) => setDocumentFile(e.target.files?.[0] ?? null)}
                        className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                      />
                    </label>

                    <button
                      type="submit"
                      disabled={uploading || !documentFile}
                      className="bg-green-700 text-white px-4 py-2 rounded-lg hover:bg-green-800 font-medium disabled:opacity-50"
                    >
                      {uploading ? 'Uploading…' : 'Upload document'}
                    </button>
                  </div>
                </form>

                <div className="mt-6 border-t pt-5">
                  <h3 className="text-md font-semibold text-green-800 mb-3">Uploaded documents</h3>
                  {documents.length === 0 ? (
                    <p className="text-sm text-gray-600">No documents uploaded yet.</p>
                  ) : (
                    <ul className="space-y-2">
                      {documents.map((doc) => (
                        <li key={doc.id} className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm">
                          <div className="flex items-center justify-between gap-3">
                            <span className="font-medium text-gray-800">{doc.filename}</span>
                            <span className="text-xs text-gray-500">{doc.doc_type}</span>
                          </div>
                          <p className="mt-1 text-xs text-gray-500">{doc.storage_uri}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </section>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
