import { HomeIcon } from 'lucide-react'

export default function Home() {
  return (
    <div className="container mx-auto p-8">
      <section className="mb-8">
        <h1 className="text-2xl font-semibold mb-4 flex items-center"><HomeIcon className="mr-2"/> Example Domain</h1>
        <p className="text-base">This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.</p>
        <p className="text-base">More information...</p>
      </section>
      <section>
        <img
          src="https://images.unsplash.com/photo-1606761947489-9363c05bd26c?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
          alt="Example Image"
          className="rounded-lg shadow-md"
        />
      </section>
    </div>
  )
}