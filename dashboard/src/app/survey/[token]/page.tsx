import SurveyFormClient from './SurveyFormClient'

export default async function SurveyPage({
  params,
}: {
  params: Promise<{ token: string }>
}) {
  const { token } = await params
  return <SurveyFormClient token={token} />
}
