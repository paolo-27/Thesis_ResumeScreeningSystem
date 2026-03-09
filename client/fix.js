const fs = require("fs");
const files = fs.readdirSync("src/components/ROOT").filter(f => f.endsWith(".tsx") || f.endsWith(".ts"));
files.forEach(file => {
  const p = "src/components/ROOT/" + file;
  let c = fs.readFileSync(p, "utf8");
  // Replace: from '../ui/card" -> from '../ui/card'
  c = c.replace(/from\s+'\.\.\/ui\/([^"'\n]+)["']/g, "from '../ui/$1'");
  fs.writeFileSync(p, c);
});
