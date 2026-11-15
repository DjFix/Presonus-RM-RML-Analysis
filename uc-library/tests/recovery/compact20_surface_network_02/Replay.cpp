#include "presonus/surface/SurfaceOutputComponent.hpp"
#include "presonus/surface/TBRoutingPageComponent.hpp"
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>
using namespace Core::Portable;
using Presonus::Surface::SurfaceOutputComponent;
using Presonus::Surface::TBRoutingPageComponent;
namespace {
void *watched = nullptr;
int freed = 0;
int borrowedDestroyed = 0;
struct CountingParam : NumericParam {
  using NumericParam::NumericParam;
  ~CountingParam() override { ++borrowedDestroyed; }
};
void init(ParamInfo &p, int tag) {
  p = {};
  p.type = ParamInfo::kInt;
  p.tag = tag;
  std::strcpy(p.name, "value");
  p.maxValue = 1000;
  p.deltaValue = 1;
}
int wrapped(int value, std::uint32_t delta) {
  auto bits = static_cast<std::uint32_t>(value) + delta;
  std::int32_t out;
  std::memcpy(&out, &bits, sizeof out);
  return out;
}
int originalTag(Parameter *p) {
  auto *a = AliasParam::cast(p);
  return a && a->getOriginal() ? a->getOriginal()->getTag() : 0;
}
} // namespace
void operator delete(void *p) noexcept {
  if (p && p == watched)
    ++freed;
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  std::string mode = argv[1];
  ParamInfo info[16]{};
  if (mode == "get") {
    int tag = std::stoi(argv[2]), mask = std::stoi(argv[3]);
    SurfaceOutputComponent page;
    for (int i = 0; i < 2; ++i)
      if (mask & (1 << i)) {
        init(info[i], 400 + i);
        page.addParameters(&info[i], 1, false);
      }
    const auto &view = page;
    auto *got = tag == 400 ? view.getDacValue() : view.getLevel();
    auto *provider = page.getParameterByTag(tag);
    if (got != provider)
      return 3;
    std::cout << (got ? got->getTag() : 0) << '\n';
  } else if (mode == "connect") {
    int index = std::stoi(argv[2]), flag = std::stoi(argv[3]);
    int kinds[2] = {std::stoi(argv[4]), std::stoi(argv[5])};
    int mask = std::stoi(argv[6]);
    Component channel;
    TBRoutingPageComponent page;
    int sourceTags[2] = {302, 300};
    for (int i = 0; i < 2; ++i) {
      init(info[i], sourceTags[i]);
      if (mask & (1 << i))
        channel.addParameters(&info[i], 1, false);
      int tag = wrapped(index, i ? 0x78u : 0x76u);
      if (kinds[i] == 1)
        page.addRoutingAlias(tag, "route");
      else if (kinds[i] == 2) {
        init(info[2 + i], tag);
        page.addParameters(&info[2 + i], 1, false);
      }
    }
    page.connectChannel(&channel, index, flag);
    for (int i = 0; i < 2; ++i)
      std::cout << originalTag(page.getParameterByTag(
                       wrapped(index, i ? 0x78u : 0x76u)))
                << (i ? '\n' : ' ');
  } else if (mode == "disconnect") {
    std::string pattern = argv[2];
    Component channel;
    init(info[0], 303);
    channel.addParameters(&info[0], 1, false);
    TBRoutingPageComponent page;
    for (std::size_t i = 0; i < pattern.size(); ++i) {
      if (pattern[i] == '1')
        page.addRoutingAlias(100 + i, "route")
            .setOriginal(channel.getParameterByTag(303));
      else if (pattern[i] == '2') {
        init(info[i + 1], 100 + i);
        page.addParameters(&info[i + 1], 1, false);
        page.retainMappable(page.getParameterByTag(100 + i));
      } else
        page.retainMappable(nullptr);
    }
    page.disconnectMappables();
    channel.getParameterByTag(303)->setValue(7, false);
    for (std::size_t i = 0; i < pattern.size(); ++i)
      if (pattern[i] == '1' && originalTag(page.getParameterByTag(100 + i)))
        return 4;
    std::cout << "0\n";
  } else if (mode == "life") {
    int deleting = std::stoi(argv[2]);
    init(info[0], 303);
    Component channel;
    channel.addParameters(&info[0], 1, false);
    auto *page = new TBRoutingPageComponent;
    page->retainMappable(channel.getParameterByTag(303));
    page->addRoutingAlias(118, "route")
        .setOriginal(channel.getParameterByTag(303));
    auto *borrowed = new CountingParam(info[0]);
    page->retainMappable(borrowed);
    watched = page;
    freed = 0;
    if (deleting)
      delete page;
    else
      page->~TBRoutingPageComponent();
    if (borrowedDestroyed != 0)
      return 5;
    channel.getParameterByTag(303)->setValue(9, false);
    std::cout << freed << '\n';
    watched = nullptr;
    if (!deleting)
      ::operator delete(page);
    delete borrowed;
    if (borrowedDestroyed != 1)
      return 6;
  } else
    return 2;
}
