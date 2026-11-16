#include "presonus/PageComponent.hpp"
#include "presonus/surface/MainScreenComponent.hpp"
#include <iostream>
#include <stdexcept>
struct PageBindings : presonus::page::Bindings {
  void *castOwner(void *, int) const override {
    throw std::logic_error("unused");
  }
  const void *currentPage(void *) const override {
    throw std::logic_error("unused");
  }
  void stopTextInput(void *, bool) const override {
    throw std::logic_error("unused");
  }
  bool isEditingText(void *) const override {
    throw std::logic_error("unused");
  }
};
struct App : presonus::mainlcd_port::Application {
  Presonus::PageComponent *findPage(int) const override {
    throw std::logic_error("unused");
  }
  void requestPage(Presonus::PageComponent *) override {
    throw std::logic_error("unused");
  }
  void showNextPage() override { throw std::logic_error("unused"); }
  int startPageTag() const override { throw std::logic_error("unused"); }
  Core::Portable::RootView *rootView(Presonus::LcdView *) const override {
    throw std::logic_error("unused");
  }
  void observeView(Presonus::LcdView *, Presonus::MainLCDComponent &) override {
    throw std::logic_error("unused");
  }
};
struct PageChild : Core::Portable::Component {
  Presonus::PageComponent page;
  bool casts;
  PageChild(PageBindings &b, int tag, bool c) : page(nullptr, b), casts(c) {
    page.bindObservedPageState(tag, 0);
  }
  void *castTo(int type) override {
    return casts && type == 1348560741 ? &page : nullptr;
  }
};
#include <bit>
#include <cstdint>
#include <vector>
using namespace Core::Portable;
struct Call {
  int id;
  std::uint32_t bits;
  bool edit;
};
static std::vector<Call> calls;
struct ProbeParam : NumericParam {
  int id;
  ProbeParam(const ParamInfo &info, int id) : NumericParam(info), id(id) {}
  void setValue(float value, bool edit = false) override {
    calls.push_back({id, std::bit_cast<std::uint32_t>(value), edit});
    NumericParam::setValue(value, edit);
  }
};
struct Receiver : Presonus::MainLCDComponent {
  using MainLCDComponent::MainLCDComponent;
  void addParameter(Parameter *p) { paramList.add(p); }
  void sortParameters() { paramList.sortAll(); }
};
int main(int argc, char **argv) {
  PageBindings bindings;
  int n, mask, params, current, next, a, b, c, sorted;
  while (std::cin >> n >> mask >> params >> current >> next >> a >> b >> c >>
         sorted) {
    App app;
    presonus::mainlcd_port::State state;
    ParamInfo infos[3]{};
    Receiver screen(app, state);
    int tags[] = {a, b, c};
    PageChild *children[3]{};
    for (int i = 0; i < n; ++i) {
      children[i] = new PageChild(bindings, tags[i], mask & (1 << i));
      screen.addChild(children[i]);
    }
    Presonus::PageComponent external(nullptr, bindings);
    auto page = [&](int index) -> Presonus::PageComponent * {
      return index < 0   ? nullptr
             : index < n ? &children[index]->page
                         : &external;
    };
    state.current = page(current);
    state.next = page(next);
    ProbeParam *p[3]{};
    for (int i = 0; i < 3; ++i)
      if (params & (1 << i)) {
        infos[i].type = ParamInfo::kFloat;
        infos[i].tag = tags[i];
        infos[i].maxValue = 1;
        infos[i].defaultValue = 0.5f;
        p[i] = new ProbeParam(infos[i], i);
        screen.addParameter(p[i]);
      }
    if (sorted)
      screen.sortParameters();
    calls.clear();
    if (argc > 1 && std::string(argv[1]) == "inspect") {
      for (int i = 0; i < n; ++i) {
        auto *v = static_cast<Presonus::PageComponent *>(
            children[i]->castTo(1348560741));
        auto *found = v ? static_cast<ProbeParam *>(
                              screen.getParameterByTag(v->getPageTag()))
                        : nullptr;
        std::cout << (v != nullptr) << " " << children[i]->page.getPageTag()
                  << " " << (found ? found->id : -1) << " ";
      }
      std::cout << "\n";
    } else {
      if (argc > 1) {
        int count;
        std::cin >> count;
        while (count--) {
          int id, edit;
          std::uint32_t bits;
          std::cin >> id >> bits >> edit;
          p[id]->setValue(std::bit_cast<float>(bits), edit);
        }
      } else
        screen.syncPageParams();
      for (int i = 0; i < 3; ++i)
        std::cout << (p[i] ? std::bit_cast<std::uint32_t>(p[i]->getValue())
                           : 0xffffffffu)
                  << " ";
      std::cout << calls.size();
      for (auto call : calls)
        std::cout << " " << call.id << " " << call.bits << " " << call.edit;
      std::cout << "\n";
    }
  }
}
