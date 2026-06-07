import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, FileText, Trash2, User, Sparkles } from 'lucide-react'
import { listResumes, uploadResume, deleteResume } from '../api/resumes'
import { listProfiles } from '../api/profiles'
import { Card, CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { PageSpinner } from '../components/ui/Spinner'
import ErrorMessage, { SuccessMessage } from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'

function UploadZone({ onUpload, loading }) {
  const fileRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [extractProfile, setExtractProfile] = useState(true)

  function handleFiles(files) {
    const file = files?.[0]
    if (!file) return
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
          border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-200
          ${dragging
            ? 'border-brand-400 bg-brand-50 scale-[1.01]'
            : 'border-slate-200 hover:border-brand-300 hover:bg-slate-50'
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
        <Upload className="h-8 w-8 text-brand-400 mx-auto mb-3" />
        <p className="text-sm font-medium text-slate-700">
          Drag & drop your resume here, or <span className="text-brand-600">click to browse</span>
        </p>
        <p className="text-xs text-slate-400 mt-1">PDF or DOCX supported</p>
      </div>

      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-600">
          <input
            type="checkbox"
            checked={extractProfile}
            onChange={(e) => setExtractProfile(e.target.checked)}
            className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
          />
          <Sparkles className="h-3.5 w-3.5 text-amber-500" />
          Extract my profile with AI
        </label>
        <Button
          onClick={() => fileRef.current?.click()}
          loading={loading}
          size="sm"
        >
          Upload Resume
        </Button>
      </div>
    </div>
  )
}

function ResumeRow({ resume, onDelete, deleting }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-100 last:border-0">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-brand-50 flex items-center justify-center">
          <FileText className="h-4 w-4 text-brand-600" />
        </div>
        <div>
          <div className="text-sm font-medium text-slate-800">{resume.file_name}</div>
          <div className="text-xs text-slate-400">{resume.content_type}</div>
        </div>
      </div>
      <Button
        variant="ghost"
        size="sm"
        loading={deleting}
        onClick={() => onDelete(resume.id)}
        className="text-rose-500 hover:text-rose-600 hover:bg-rose-50"
      >
        <Trash2 className="h-3.5 w-3.5" />
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
    <div className="space-y-4">
      <div>
        <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1.5">
          Target Roles
        </div>
        <div className="flex flex-wrap gap-1.5">
          {(profile.target_roles ?? []).length > 0 ? (
            profile.target_roles.map((role) => (
              <span
                key={role}
                className="inline-flex px-2.5 py-1 rounded-full text-xs bg-brand-100 text-brand-700 font-medium"
              >
                {role}
              </span>
            ))
          ) : (
            <span className="text-xs text-slate-400">Not extracted</span>
          )}
        </div>
      </div>

      {profile.experience_years != null && (
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">
            Experience
          </div>
          <div className="text-sm text-slate-800">{profile.experience_years} years</div>
        </div>
      )}

      {allSkills.length > 0 && (
        <div>
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1.5">
            Skills
          </div>
          <div className="flex flex-wrap gap-1.5">
            {allSkills.slice(0, 20).map((skill) => (
              <span
                key={skill}
                className="inline-flex px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-600"
              >
                {skill}
              </span>
            ))}
            {allSkills.length > 20 && (
              <span className="text-xs text-slate-400">+{allSkills.length - 20} more</span>
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

  const resumes = resumesQ.data?.items ?? []
  const profiles = profilesQ.data?.items ?? []

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">My Resume</h1>
        <p className="text-slate-500 mt-1">Upload your resume and let AI build your candidate profile</p>
      </div>

      <div className="space-y-6">
        {/* Upload */}
        <Card>
          <CardHeader title="Upload Resume" subtitle="PDF or DOCX, up to 10MB" />
          {uploadStatus?.type === 'success' && (
            <SuccessMessage message={uploadStatus.message} className="mb-4" />
          )}
          {uploadStatus?.type === 'error' && (
            <ErrorMessage message={uploadStatus.message} className="mb-4" />
          )}
          <UploadZone
            loading={uploadMut.isPending}
            onUpload={(file, extractProfile) => {
              setUploadStatus(null)
              uploadMut.mutate({ file, extractProfile })
            }}
          />
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Uploaded resumes */}
          <Card>
            <CardHeader title="Uploaded Resumes" subtitle={`${resumes.length} file${resumes.length !== 1 ? 's' : ''}`} />
            {resumesQ.isLoading ? (
              <PageSpinner />
            ) : resumes.length === 0 ? (
              <EmptyState
                icon="📄"
                title="No resumes yet"
                description="Upload your resume above to get started."
              />
            ) : (
              resumes.map((r) => (
                <ResumeRow
                  key={r.id}
                  resume={r}
                  onDelete={(id) => deleteMut.mutate(id)}
                  deleting={deleteMut.isPending && deleteMut.variables === r.id}
                />
              ))
            )}
          </Card>

          {/* Profile */}
          <Card>
            <CardHeader
              title="Candidate Profile"
              subtitle="Extracted by AI from your resume"
              action={
                <div className="h-7 w-7 rounded-full bg-amber-100 flex items-center justify-center">
                  <User className="h-4 w-4 text-amber-600" />
                </div>
              }
            />
            {profilesQ.isLoading ? (
              <PageSpinner />
            ) : profiles.length === 0 ? (
              <EmptyState
                icon="✨"
                title="No profile yet"
                description="Upload a resume with AI extraction enabled."
              />
            ) : (
              <ProfileCard profile={profiles[0]} />
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
