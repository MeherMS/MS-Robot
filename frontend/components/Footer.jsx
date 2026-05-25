export default function Footer() {
  const currentYear = new Date().getFullYear();

  const links = [
    {
      name: "Email",
      href: "mailto:selmi.ms1995@gmail.com",
      icon: "✉️",
    },
    {
      name: "GitHub",
      href: "https://github.com/meherms",
      icon: "🔗",
    },
    {
      name: "Portfolio",
      href: "https://meherms.github.io",
      icon: "🌐",
    },
    {
      name: "LinkedIn",
      href: "https://linkedin.com/in/meherms",
      icon: "💼",
    },
  ];

  return (
    <footer className="w-full border-t border-gray-200 bg-white py-6 px-4 mt-8">
      <div className="mx-auto max-w-2xl">
       {/* Links Section */}
<div className="flex flex-wrap justify-center gap-4 mb-4 sm:gap-6">
  {links.map((link) => (
    <a
      key={link.name}
      href={link.href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-gray-600 hover:text-gray-900 transition-colors text-sm font-medium flex items-center gap-1"
    >
      <span>{link.icon}</span>
      <span>{link.name}</span>
    </a>
  ))}
</div>

        {/* Copyright Section */}
        <div className="border-t border-gray-100 pt-4 text-center">
          <p className="text-gray-500 text-xs">
            © {currentYear} Built by Meher Selmi
          </p>
        </div>
      </div>
    </footer>
  );
}