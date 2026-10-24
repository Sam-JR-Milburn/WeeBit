import SubmitLinkForm from "@/components/SubmitLinkForm";
import DoodleBackground from "@/components/DoodleBackground";

export default function Home() {
  return (
      <main className={"flex-1 flex items-center justify-center p-4 sm:p-6"}>
          <SubmitLinkForm />
      </main>
  );
}
