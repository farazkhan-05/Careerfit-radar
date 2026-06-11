import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, Sparkles, Trash2, Upload, User } from 'lucide-react'
import { listResumes, uploadResume, deleteResume, deleteAllResumes } from '../api/resumes'
import { listProfiles, deleteProfile, deleteAllProfiles } from '../api/profiles'
import { Card, CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { PageSpinner } from '../components/ui/Spinner'
import ErrorMessage, { SuccessMessage } from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'

const MAX_RESUME_BYTES = 10 * 1024 * 1024

function UploadZone({ onUpload, onReject, loading }) {
  const fileRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [extractProfile, setExtractProfile] = useState(true)

  function handleFiles(files) {
    const file = files?.[0]
    if (!file) return
    if (file.size > MAX_RESUME_BYTES) {
      onReject(`Resume file is too large. Maximum size is ${Math.round(MAX_RESUME_BYTES / 1024 / 1024)}MB.`)
      return
    }
    onUpload(file, extractProfile)
  }

  return (
    <div className="space-y-4">
      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFiles(e.dataTransfer.files)
        }}
        className={`
          group relative cursor-pointer overflow-hidden rounded-lg border-2 border-dashed p-8 text-center transition-all duration-200 sm:p-10
          ${dragging
            ? 'border-brand-500 bg-brand-100 shadow-[6px_6px_0_rgba(83,208,162,0.30)]'
            : 'border-ink/15 bg-white hover:-translate-y-0.5 hover:border-ink hover:shadow-[6px_6px_0_rgba(24,33,47,0.08)]'
          }
        `}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-lg border border-ink/10 bg-sun text-ink transition-transform group-hover:-rotate-2">
          <Upload className="h-7 w-7" />
        </div>
        <p className="font-display text-xl font-bold text-ink">Drop your resume here</p>
        <p className="mt-2 text-sm font-medium text-muted">PDF, DOCX, or TXT. Click the panel to browse.</p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm font-bold text-ink">
          <input
            type="checkbox"
            checked={extractProfile}
            onChange={(e) => setExtractProfile(e.target.checked)}
            className="h-4 w-4 rounded border-ink/20 text-brand-500 focus:ring-brand-300"
          />
          <Sparkles className="h-4 w-4 text-amber-600" />
          Extract profile
        </label>
        <Button onClick={() => fileRef.current?.click()} loading={loading}>
          <Upload className="h-4 w-4" />
          Upload resume
        </Button>
      </div>
    </div>
  )
}

function ResumeRow({ resume, onDelete, deleting }) {
  return (
    <div className="grid gap-3 border-b border-ink/10 py-4 last:border-0 sm:grid-cols-[1fr_auto] sm:items-center">
      <div className="flex min-w-0 items-center gap-3">
        <div className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-lg bg-sky/20 text-blue-700">
          <FileText className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-bold text-ink">{resume.file_name}</div>
          <div className="text-xs font-semibold text-muted">{resume.content_type}</div>
        </div>
      </div>
      <Button
        variant="ghost"
        size="sm"
        loading={deleting}
        onClick={() => onDelete(resume.id)}
        className="justify-self-start text-rose-600 hover:bg-coral/10 hover:text-rose-700 sm:justify-self-end"
        title="Delete resume"
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  )
}

function ProfileCard({ profile }) {
  const skills = profile.skills ?? {}
  const allSkills = [
    ...(skills.technical ?? []),
    ...(skills.languages ?? []),
    ...(skills.frameworks ?? []),
  ].filter(Boolean)

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-2 text-[10px] font-extrabold uppercase tracking-[0.18em] text-muted">
          Target roles
        </div>
        <div className="flex flex-wrap gap-2">
          {(profile.target_roles ?? []).length > 0 ? (
            profile.target_roles.map((role) => (
              <span
                key={role}
                className="inline-flex rounded-md border border-brand-500/25 bg-brand-100 px-2.5 py-1 text-xs font-bold text-brand-800"
              >
                {role}
              </span>
            ))
          ) : (
            <span className="text-sm font-medium text-muted">Not extracted</span>
          )}
        </div>
      </div>

      {profile.experience_years != null && (
        <div className="rounded-lg border border-ink/10 bg-white p-4">
          <div className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-muted">
            Experience
          </div>
          <div className="mt-1 font-display text-3xl font-bold text-ink">{profile.experience_years}</div>
          <div className="text-sm font-bold text-muted">years</div>
        </div>
      )}

      {allSkills.length > 0 && (
        <div>
          <div className="mb-2 text-[10px] font-extrabold uppercase tracking-[0.18em] text-muted">
            Skills
          </div>
          <div className="flex flex-wrap gap-2">
            {allSkills.slice(0, 20).map((skill) => (
              <span
                key={skill}
                className="inline-flex rounded-md border border-ink/10 bg-white px-2.5 py-1 text-xs font-semibold text-muted"
              >
                {skill}
              </span>
            ))}
            {allSkills.length > 20 && (
              <span className="inline-flex rounded-md border border-ink/10 bg-sun/20 px-2.5 py-1 text-xs font-bold text-ink">
                +{allSkills.length - 20} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Resume() {
  const queryClient = useQueryClient()
  const [uploadStatus, setUploadStatus] = useState(null)

  const resumesQ = useQuery({ queryKey: ['resumes'], queryFn: () => listResumes(50, 0) })
  const profilesQ = useQuery({ queryKey: ['profiles'], queryFn: () => listProfiles(5, 0) })

  const uploadMut = useMutation({
    mutationFn: ({ file, extractProfile }) => uploadResume(file, extractProfile),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] })
      queryClient.invalidateQueries({ queryKey: ['profiles'] })
      const profileNote = data.profile_id
        ? ' Profile extracted.'
        : data.profile_error
          ? ` Profile extraction failed: ${data.profile_error}`
          : ''
      setUploadStatus({ type: 'success', message: `Resume uploaded (${data.chunk_count} sections).${profileNote}` })
    },
    onError: (err) => setUploadStatus({ type: 'error', message: err.message }),
  })

  const deleteMut = useMutation({
    mutationFn: (id) => deleteResume(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] })
      queryClient.invalidateQueries({ queryKey: ['profiles'] })
    },
  })

  const deleteAllResumesMut = useMutation({
    mutationFn: deleteAllResumes,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] })
      queryClient.invalidateQueries({ queryKey: ['profiles'] })
      setUploadStatus({ type: 'success', message: 'All resumes and profiles deleted.' })
    },
    onError: (err) => setUploadStatus({ type: 'error', message: err.message }),
  })

  const deleteProfileMut = useMutation({
    mutationFn: (id) => deleteProfile(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profiles'] }),
  })

  const deleteAllProfilesMut = useMutation({
    mutationFn: deleteAllProfiles,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profiles'] }),
  })

  const resumes = resumesQ.data?.items ?? []
  const profiles = profilesQ.data?.items ?? []

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="mb-6">
        <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-muted">Candidate file</p>
        <h1 className="mt-1 font-display text-4xl font-bold leading-tight text-ink">Resume and profile</h1>
        <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-muted">
          Keep the source document and extracted matching profile in one clean place.
        </p>
      </header>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="space-y-5">
          <Card accent="var(--sun)">
            <CardHeader title="Upload resume" subtitle="PDF, DOCX, or TXT up to 10MB" eyebrow="Input" />
            {uploadStatus?.type === 'success' && (
              <SuccessMessage message={uploadStatus.message} className="mb-4" />
            )}
            {uploadStatus?.type === 'error' && (
              <ErrorMessage message={uploadStatus.message} className="mb-4" />
            )}
            <UploadZone
              loading={uploadMut.isPending}
              onReject={(message) => setUploadStatus({ type: 'error', message })}
              onUpload={(file, extractProfile) => {
                setUploadStatus(null)
                uploadMut.mutate({ file, extractProfile })
              }}
            />
          </Card>

          <Card accent="var(--sky)">
            <CardHeader
              title="Uploaded files"
              subtitle={`${resumes.length} file${resumes.length !== 1 ? 's' : ''}`}
              eyebrow="Library"
              action={
                resumes.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    loading={deleteAllResumesMut.isPending}
                    onClick={() => {
                      if (window.confirm('Delete all resumes and profiles? This cannot be undone.')) {
                        deleteAllResumesMut.mutate()
                      }
                    }}
                    className="text-rose-600 hover:bg-coral/10 hover:text-rose-700"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete all
                  </Button>
                )
              }
            />
            {resumesQ.isLoading ? (
              <PageSpinner />
            ) : resumes.length === 0 ? (
              <EmptyState
                icon={FileText}
                title="No resumes yet"
                description="Upload a resume above to start building your profile."
              />
            ) : (
              resumes.map((resume) => (
                <ResumeRow
                  key={resume.id}
                  resume={resume}
                  onDelete={(id) => deleteMut.mutate(id)}
                  deleting={deleteMut.isPending && deleteMut.variables === resume.id}
                />
              ))
            )}
          </Card>
        </div>

        <aside className="xl:sticky xl:top-8 xl:self-start">
          <Card accent="var(--mint)">
            <CardHeader
              title="Candidate profile"
              subtitle="Extracted from uploaded resume content"
              eyebrow="Matching brain"
              action={
                <div className="flex items-center gap-2">
                  {profiles.length > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={deleteAllProfilesMut.isPending}
                      onClick={() => {
                        if (window.confirm('Delete all extracted profiles?')) {
                          deleteAllProfilesMut.mutate()
                        }
                      }}
                      className="text-rose-600 hover:bg-coral/10 hover:text-rose-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                  <div className="grid h-9 w-9 place-items-center rounded-lg bg-mint/20 text-brand-800">
                    <User className="h-5 w-5" />
                  </div>
                </div>
              }
            />
            {profilesQ.isLoading ? (
              <PageSpinner />
            ) : profiles.length === 0 ? (
              <EmptyState
                icon={Sparkles}
                title="No profile yet"
                description="Enable extraction while uploading to create one."
              />
            ) : (
              <div className="space-y-6">
                {profiles.map((profile) => (
                  <div key={profile.id} className="relative rounded-lg border border-ink/10 bg-white/70 p-4">
                    <button
                      onClick={() => deleteProfileMut.mutate(profile.id)}
                      disabled={deleteProfileMut.isPending && deleteProfileMut.variables === profile.id}
                      className="absolute right-3 top-3 rounded-lg border border-transparent p-2 text-rose-600 transition-colors hover:border-coral/20 hover:bg-coral/10"
                      title="Delete profile"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                    <ProfileCard profile={profile} />
                  </div>
                ))}
              </div>
            )}
          </Card>
        </aside>
      </div>
    </div>
  )
}
