interface BreadcrumbItem {
  label: string;
  href?: string;
}

export default function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="breadcrumb">
      <ol className="breadcrumb">
        {items.map((item, i) =>
          item.href ? (
            <li key={i} className="breadcrumb-item">
              <a className="text-decoration-none" href={item.href}>
                {item.label}
              </a>
            </li>
          ) : (
            <li key={i} className="breadcrumb-item active" aria-current="page">
              {item.label}
            </li>
          )
        )}
      </ol>
    </nav>
  );
}
