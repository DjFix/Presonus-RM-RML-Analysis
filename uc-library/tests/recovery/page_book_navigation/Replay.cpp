#include "presonus/panel/Book.hpp"
#include "presonus/panel/FieldElement.hpp"
#include "presonus/panel/FillElement.hpp"
#include "presonus/panel/LCDManager.hpp"
#include "presonus/panel/StaticElement.hpp"
#include "presonus/panel/key_input_provider.hpp"
#include "presonus/surface_panel/BitmapDrawing.hpp"
#include <cstring>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
using namespace Presonus::Panel;
namespace {
std::string quote(const std::string &s) {
  std::string r = "\"";
  for (char c : s) {
    if (c == '"' || c == '\\')
      r += '\\';
    r += c;
  }
  return r + '"';
}
template <class T> std::string array(const std::vector<T> &v) {
  std::ostringstream o;
  o << '[';
  bool first = true;
  for (const auto &x : v) {
    if (!first)
      o << ',';
    first = false;
    o << x;
  }
  o << ']';
  return o.str();
}
std::string strings(const std::vector<std::string> &v) {
  std::vector<std::string> q;
  for (auto &s : v)
    q.push_back(quote(s));
  return array(q);
}
std::string rect(const Rectangle &r) {
  return array(std::vector<int>{r.x, r.y, r.width, r.height});
}
struct Json {
  bool first = true;
  Json() { std::cout << '{'; }
  ~Json() { std::cout << "}\n"; }
  void add(const char *k, const std::string &v) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << quote(k) << ':' << v;
  }
  void num(const char *k, int v) { add(k, std::to_string(v)); }
};
// Explicit display observation boundary for comparing application dispatch.
// The separate provider mode below exercises actual BitmapDisplay buffers.
class Display : public IDisplay {
public:
  mutable std::vector<std::string> events;
  int x = 0, y = 0;
  void setPort(IPanelIO *) override {}
  int getScreenWidth() const override { return 192; }
  int getScreenHeight() const override { return 64; }
  int getCharHeight() const override { return 8; }
  int getTextBoxHeight() const override {
    events.push_back("height");
    return 9;
  }
  void copyBits(char *, const char *, const Point &,
                const Rectangle &) override {}
  void copyBits(const char *, const Point &p, const Rectangle &r) override {
    copy("copy", p, r);
  }
  void getScreenBits(char *, const Point &p, const Rectangle &r) override {
    copy("capture", p, r);
  }
  void copy(const char *k, const Point &p, const Rectangle &r) {
    events.push_back(std::string(k) + " " + std::to_string(p.x) + " " +
                     std::to_string(p.y) + " " + std::to_string(r.x) + " " +
                     std::to_string(r.y) + " " + std::to_string(r.width) + " " +
                     std::to_string(r.height));
  }
  void clear() override { events.push_back("clear"); }
  void fillRect(const Rectangle &r) override { shape("fill", r); }
  void eraseRect(const Rectangle &r) override { shape("erase", r); }
  void invertRect(const Rectangle &r) override { shape("invert", r); }
  void shape(const char *k, const Rectangle &r) {
    events.push_back(std::string(k) + " " + std::to_string(r.x) + " " +
                     std::to_string(r.y) + " " + std::to_string(r.width) + " " +
                     std::to_string(r.height));
  }
  void setPixel(int, int, bool) override {}
  bool getPixel(int, int) const override { return false; }
  void drawText(int, int, const char *, int, Rectangle *) override {}
  void drawString(const char *t, int width, Rectangle *r) override {
    events.push_back("text " + std::string(t) + " " + std::to_string(width) +
                     " " + std::to_string(r != nullptr));
    if (r)
      *r = {x, y, int(std::strlen(t)) * 6, *t ? 8 : 0};
  }
  char *getBitmapData() const override { return nullptr; }
  int pixelLength(const char *t) override {
    events.push_back("pixel " + std::string(t));
    return int(std::strlen(t)) * 6;
  }
  int setPen(int) override { return 0; }
  int setTextColor(int c) override {
    events.push_back("color " + std::to_string(c));
    return 0;
  }
  void moveTo(int a, int b) override {
    x = a;
    y = b;
    events.push_back("move " + std::to_string(a) + " " + std::to_string(b));
  }
  void getPos(int &a, int &b) const override {
    a = x;
    b = y;
  }
  void update(bool force) override {
    events.push_back("update " + std::to_string(force));
  }
};
struct Key : IKeyInputDelegate {
  bool pressed = false;
  bool altKeyPressed() const override { return pressed; }
};
struct Lookup : ILCDDelegate {
  Core::Portable::Parameter *value = nullptr;
  Core::Portable::Parameter *
  lookupElementParameter(const char *) const override {
    return value;
  }
};
ElementInfo info(int selector = 2, const char *name = "level") {
  ElementInfo i;
  auto put = [&](int off, int v) {
    std::memcpy(i.observation.data() + off, &v, 4);
  };
  put(0, selector);
  put(4, 10);
  put(8, 20);
  put(12, 30);
  put(16, 8);
  std::strcpy(reinterpret_cast<char *>(i.observation.data() + 20), name);
  i.observation[92] = 1;
  return i;
}
bool has(const std::string &s, const char *k) {
  return s.find(k) != std::string::npos;
}
} // namespace
int main(int argc, char **argv) {
  if (argc == 1) {
    BitmapDisplay display;
    display.setPen(0);
    display.clear();
    display.fillRect({2, 2, 12, 8});
    if (!display.getPixel(3, 3))
      throw std::runtime_error("actual fill");
    char cache[3072]{};
    display.getScreenBits(cache, {0, 0}, {2, 2, 12, 8});
    display.eraseRect({2, 2, 12, 8});
    display.copyBits(cache, {2, 2}, {0, 0, 12, 8});
    if (!display.getPixel(3, 3))
      throw std::runtime_error("actual cache");
    auto i = info(0, "hello");
    StaticElement element(i);
    element.draw(display);
    element.draw(display);
    std::cout << "actual-bitmap-fill-copy-static-cache-ok\n";
    return 0;
  }
  const std::string n = argv[1];
  const int variant = std::stoi(argv[2]);
  Display display;
  Core::Portable::ParamInfo parameterInfo{};
  parameterInfo.tag = 7;
  Core::Portable::StringParam parameter(parameterInfo);
  parameter.enable(!(has(n, "7Element8editable") && variant == 2) &&
                   !(has(n, "4Page") && variant == 5));
  Lookup lookup;
  FieldElement::defaultLookupManager().setDelegate(&lookup);
  TextEntryElement::setEncoderParam(&parameter);
  // Clear every borrowed global before its provider owner is destroyed.
  struct Reset {
    ~Reset() {
      TextEntryElement::setEncoderParam(nullptr);
      FieldElement::defaultLookupManager().setDelegate(nullptr);
      presonus::panel::KeyInputProviderAccess::bind(
          KeyInputProvider::instance(), nullptr);
    }
  } reset;
  if (has(n, "4Page")) {
    const bool ctor = has(n, "PageC1") || has(n, "PageC2");
    if (ctor) {
      int selector = variant < 5 ? variant : variant < 7 ? 0 : 1;
      const char *names[] = {
          "level",           "level",          "level",
          "level",           "level",          "Link ID:",
          "Subgroup Merge:", "global/link_id", "global/subgroupmerge"};
      auto record = info(selector, names[variant]);
      Page p("factory", &record, 1);
      Json j;
      j.num("count", p.elements().size());
      j.add("name", quote(p.getName()));
      j.num("selector", selector);
      return 0;
    }
    Page p(Page::Elements{}, "page");
    std::vector<Element *> children;
    if (variant)
      for (int i = 0; i < (variant == 3 ? 32 : 2); ++i) {
        auto record = info();
        if (variant == 6) {
          auto field = std::make_unique<FieldElement>(record);
          children.push_back(field.get());
          p.add(field.release());
          continue;
        }
        auto entry = std::make_unique<TextEntryElement>(record);
        entry->setString("abc");
        auto child = std::make_unique<Page::TextEntrySelection>(
            record, std::move(entry));
        children.push_back(child.get());
        p.add(child.release());
      }
    if (variant == 6) {
      lookup.value = &parameter;
      parameter.fromString("abc");
    }
    if (variant == 2) {
      p.activeElement(children[0]);
      const_cast<presonus::panel::portable::TextEntryState &>(
          dynamic_cast<Page::TextEntrySelection *>(children[0])
              ->entry()
              .textState())
          .cursor = 32;
    }
    if (variant == 4 || variant == 5)
      p.activeElement(children.back());
    int result = -1;
    if (has(n, "3add")) {
      p.add(new FillElement(info()));
      Json j;
      j.num("count", p.elements().size());
      return 0;
    }
    if (has(n, "14setActiveParam"))
      result = has(n, "EPN4")
                   ? p.setActiveParam(variant == 4 ? nullptr : &parameter)
                   : p.setActiveParam(variant == 4 ? 99u : 7u);
    else if (has(n, "9nextField"))
      p.nextField();
    else if (has(n, "13previousField"))
      p.previousField();
    else if (has(n, "3tap"))
      p.tap();
    else if (has(n, "12deltaEncoder"))
      p.deltaEncoder(2);
    else if (has(n, "8activate"))
      p.activate("before");
    else if (has(n, "12updateParams"))
      p.updateParams();
    else if (has(n, "6update"))
      p.update(display);
    std::vector<int> cursors, activations, dirty;
    int active = -1;
    for (int i = 0; i < int(children.size()); ++i) {
      auto *c = children[i];
      if (p.selectedElement() == c)
        active = i;
      if (auto *text = dynamic_cast<Page::TextEntrySelection *>(c)) {
        cursors.push_back(text->entry().textState().cursor);
        activations.push_back(
            text->entry().fieldElement()->elementState().activation);
        dirty.push_back(text->entry().fieldElement()->elementState().dirty);
      } else {
        cursors.push_back(0);
        activations.push_back(c->elementState().activation);
        dirty.push_back(c->elementState().dirty);
      }
    }
    Json j;
    j.num("active", active);
    j.add("cursors", array(cursors));
    j.add("activations", array(activations));
    j.add("dirty", array(dirty));
    j.num("redraw", has(n, "6update") ? 0 : 1);
    j.add("previous", quote(p.previousPageName()));
    j.add("events", strings(display.events));
    if (result >= 0)
      j.num("return", result);
  } else if (has(n, "4Book")) {
    Book book(0);
    Page first(Page::Elements{}, "first"), second(Page::Elements{}, "second");
    if (variant != 5 || has(n, "12makeValidPos") || has(n, "7prepare")) {
      book.add(&first);
      book.add(&second);
    }
    second.setEnabled(variant != 0);
    second.setRequiresAltKey(variant == 2);
    Key key;
    key.pressed = variant == 1;
    presonus::panel::KeyInputProviderAccess::bind(KeyInputProvider::instance(),
                                                  &key);
    // Establish the observed previous slot without changing active position.
    // The existing portable inspector is deliberately distinct from ARM layout.
    presonus::panel::BookInspector::setPreviousPosition(book, 1);
    if (has(n, "12makeValidPos") || has(n, "7prepare"))
      first.setEnabled(false);
    int result = -1;
    if (has(n, "11canShowPage"))
      result = book.canShowPage(variant == 3 ? -1 : variant == 4 ? 2 : 1);
    else if (has(n, "12switchToPageEPKc"))
      book.switchToPage("second");
    else if (has(n, "12switchToPageEi"))
      book.switchToPage(variant == 3 ? -1 : variant == 4 ? 2 : 1);
    else if (has(n, "12makeValidPos"))
      book.makeValidPos();
    else if (has(n, "7prepare"))
      book.prepare();
    else if (has(n, "16loadPreviousPage")) {
      book.loadPreviousPage();
    } else if (has(n, "3tap"))
      book.tap();
    else if (has(n, "4next"))
      book.next();
    else if (has(n, "8previous"))
      book.previous();
    else if (has(n, "5store"))
      book.store();
    else if (has(n, "6recall"))
      book.recall();
    else if (has(n, "6pageup"))
      book.pageup();
    else if (has(n, "8pagedown"))
      book.pagedown();
    else if (has(n, "12deltaEncoder"))
      book.deltaEncoder(2);
    else if (has(n, "6update"))
      book.update(display);
    Json j;
    j.num("position", presonus::panel::BookInspector::zero90(book));
    j.num("previous", presonus::panel::BookInspector::zero94(book));
    j.add("previousNames",
          strings({first.previousPageName(), second.previousPageName()}));
    j.add("redraw", array(std::vector<int>{
                        has(n, "6update") && variant != 5 ? 0 : 1, 1}));
    j.add("events", strings(display.events));
    if (result >= 0)
      j.num("return", result);
  } else if (has(n, "FillElementC")) {
    FillElement e(info());
    Json j;
    j.add("bounds", rect(e.fillRectangle()));
    j.num("dirty", e.elementState().dirty);
  } else if (has(n, "StaticElementC")) {
    StaticElement e(info());
    Json j;
    j.add("bounds", rect(e.drawingBounds()));
    j.num("dirty", e.elementState().dirty);
  } else if (has(n, "8editable")) {
    lookup.value = variant ? &parameter : nullptr;
    auto record = info();
    if (variant == 3)
      record.observation[92] = 0;
    FieldElement e(record);
    Json j;
    j.num("result", e.editable());
  } else if (has(n, "7Element4draw")) {
    Element e(info());
    e.activate(variant);
    e.draw(display);
    Json j;
    j.num("dirty", e.elementState().dirty);
    j.add("events", strings(display.events));
  } else {
    auto record = info();
    std::memcpy(record.observation.data() + 84, &variant, 4);
    StaticElement e(record);
    if (has(n, "13StaticElement6render"))
      e.render(display, variant == 2);
    else {
      e.draw(display);
      e.draw(display);
    }
    Json j;
    j.add("bounds", rect(e.drawingBounds()));
    j.num("dirty", e.elementState().dirty);
    j.add("events", strings(display.events));
  }
}
