import GitHubLogo from "@/components/GitHubLogo";

export default function Header() {
    return (
        <div>
            <header
                style={{ backgroundColor: "#141414" }}
                className="h-[8vh] w-full flex items-center justify-between px-6 border-b border-[#ffffff]"
            >
                <a
                    href={"/"}
                >
                    <h2 className="text-xl font-bold text-white">WeeBit</h2>
                </a>
                <nav className={"flex flex-row items-center space-x-6 font-bold"}>
                    <a
                    href="/analytics"
                    >
                        <h3>
                            Analytics
                        </h3>
                    </a>
                    <a
                        className="p-1 rounded-md transition-colors flex items-center justify-center"
                        href="https://github.com/Sam-JR-Milburn/WeeBit"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        <GitHubLogo className="h-8 w-8 text-white hover:text-blue-400 transition-colors duration-200" />
                    </a>
                </nav>
            </header>
        </div>
    );
}