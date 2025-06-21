import CompanyLogos from '../components/CompanyLogos'

export default function Home() {
  return (
    <div className="container mx-auto py-8">
      <section className="hero-section text-center">
        <h1 className="text-2xl font-semibold mb-4">Y Combinator</h1>
        <p className="text-base">Make something people want.</p>
        <p>Apply to YC</p>
        <p>5,000 funded startups $800B combined valuation</p>
        <p>Top YC companies</p>
        <img
          src="https://images.unsplash.com/photo-1523895664952-72ffc5e5624d?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
          alt="YC Hero Image"
          className="mx-auto rounded-lg shadow-md mt-8"
        />
      </section>

      <section className="company-logos-section mt-12">
        <CompanyLogos />
      </section>
    </div>
  )
}