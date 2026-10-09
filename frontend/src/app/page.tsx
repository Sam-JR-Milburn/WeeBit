import Header from "@/components/Header";
import SubmitLinkForm from "@/components/SubmitLinkForm";

export default function Home() {
  return (
      <div
          className={"h-screen w-screen flex flex-col overflow-hidden text-slate-100"}>
          <Header />
          <main className={"flex-1 flex items-center justify-center p-4 sm:p-6"}>
              <SubmitLinkForm />
          </main>
      </div>
  );
}
