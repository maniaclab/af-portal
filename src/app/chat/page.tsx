import { requireMember } from "@/lib/auth/guards";
import Breadcrumb from "@/components/ui/Breadcrumb";

export const metadata = { title: "Analysis Facility - Chat" };

export default async function ChatPage() {
  const { session } = await requireMember();
  const unixName = session.unix_name;

  return (
    <section style={{ overflow: "hidden" }}>
      <div className="container">
        <Breadcrumb
          items={[
            { label: "Home", href: "/" },
            { label: "Chat" },
          ]}
        />
        {unixName ? (
          <iframe
            id="chat"
            title="AF ChatGPT"
            width="100%"
            height="750px"
            allow="clipboard-read; clipboard-write"
            src={`https://afchatkit.af.atlas-ml.org/?user=${encodeURIComponent(unixName)}`}
          />
        ) : (
          <p>Only accounts with a valid identity can use ChatGPT integration</p>
        )}
      </div>
    </section>
  );
}
