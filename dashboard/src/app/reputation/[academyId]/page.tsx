import ReputationDashboardClient from './ReputationDashboardClient'

export default async function ReputationAcademyPage({
  params,
}: {
  params: Promise<{ academyId: string }>
}) {
  const { academyId } = await params
  return <ReputationDashboardClient academyId={academyId} />
}
