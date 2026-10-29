// One flat, neutral accent used for every subject card -- kept as a function
// (rather than inlined styles) so pages don't need to change if this ever
// needs to vary again.
const FLAT = { bg: "bg-gray-800", ring: "ring-gray-700", text: "text-[#20bcd8]", bar: "bg-[#20bcd8]" };

export function colorForSubject(_name: string) {
  return FLAT;
}

export function initialsForSubject(name: string): string {
  const words = name.trim().split(/\s+/);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}
