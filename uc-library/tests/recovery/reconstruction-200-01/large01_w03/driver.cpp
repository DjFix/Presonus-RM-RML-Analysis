#include "presonus/reconstruction200/large01_w03.hpp"
#include <bit>
#include <iostream>
#include <map>
#include <memory>
#include <vector>
using U = std::uint32_t;
int main() {
  int method;
  while (std::cin >> method) {
    auto read = []() {
      U x;
      std::cin >> x;
      return x;
    };
    std::vector<U> out;
    if (method == 1) {
      int i;
      std::cin >> i;
      U v = read();
      Presonus::Dsp::ShelbyGEQController x;
      if (i >= 0 && i <= 32)
        x.portableValues()[i] = std::bit_cast<float>(v);
      out = {std::bit_cast<U>(x.getValue(i))};
    } else if (method == 2) {
      U n = read();
      Presonus::Dsp::EQController x(presonus::dsp::EQTypePortTag{});
      x.portableBands().resize(n);
      out = {U(x.getNumBands())};
    } else if (method == 3) {
      U n = read();
      int i;
      std::cin >> i;
      U old = read(), edge = read(), dirty = read();
      Presonus::Dsp::EQController x(presonus::dsp::EQTypePortTag{});
      x.portableBands().resize(n);
      x.sourceState().processDirty = dirty;
      for (auto &b : x.portableBands()) {
        b.type = old;
        b.edgeSelectable = edge;
      }
      x.triggerOption(i);
      out.push_back(x.sourceState().processDirty);
      for (auto &b : x.portableBands())
        out.push_back(b.type);
    } else if (method == 4) {
      U n = read(), old = read(), rate = read(), dirty = read();
      Presonus::Dsp::EQController x(presonus::dsp::EQTypePortTag{});
      x.portableBands().resize(n);
      x.sourceState().processRateBits = old;
      x.sourceState().processDirty = dirty;
      alignas(8) U property[3] = {0, 0, rate};
      x.setupProcess(
          *reinterpret_cast<const Presonus::Dsp::SetupProperty *>(property));
      // Provider state is observed after actual Biquad::setup, not a callback.
      // Unchanged-rate path has no calls and no calculator reads.
      bool changed = std::bit_cast<float>(old) != std::bit_cast<float>(rate);
      out = {x.sourceState().processRateBits, x.sourceState().processDirty,
             changed ? n : 0};
      if (changed)
        for (U i = 0; i < n; ++i) {
          auto &s = x.portableBands()[i].calculator.portableState();
          auto wide = std::bit_cast<std::uint64_t>(s.rate);
          out.insert(out.end(), {32, U(wide), U(wide >> 32), i});
        }
      for (auto &b : x.portableBands())
        out.push_back(b.dirty);
    } else if (method == 5) {
      Presonus::Dsp::ShelbyGEQController x;
      out = {U(x.getNumParameters())};
    } else if (method == 6 || method == 7) {
      U slots[6];
      for (auto &v : slots)
        v = read();
      U query = read();
      // Borrowed genuine pinned CCL Parameter instances, tokens are fixture
      // IDs.
      Core::Portable::ParamInfo info{};
      std::map<U, std::unique_ptr<Core::Portable::Parameter>> params;
      auto pointer = [&](U id) -> Core::Portable::Parameter * {
        if (!id)
          return nullptr;
        if (!params.count(id))
          params[id] = std::make_unique<Core::Portable::NumericParam>(info);
        return params[id].get();
      };
      Presonus::EQControl control(presonus::dsp::EQControlBiquadPortTag{});
      control.portableParameterState().emplace_back();
      auto &b = control.portableParameterState().back();
      Core::Portable::Parameter **dest[] = {&b.gain,  &b.q,     &b.frequency,
                                            &b.slot3, &b.slot4, &b.slot5};
      for (int i = 0; i < 6; ++i)
        *dest[i] = pointer(slots[i]);
      if (method == 6)
        out = {U(b.contains(pointer(query)))};
      else {
        b.zeroParam(pointer(query));
        for (auto p : dest) {
          U id = 0;
          for (auto &[key, value] : params)
            if (value.get() == *p)
              id = key;
          out.push_back(id);
        }
      }
    } else if (method == 8) {
      U flag = read();
      Presonus::EQControl x(presonus::dsp::EQControlBiquadPortTag{});
      // setBufferedDraw performs real draw-provider work and is separately
      // validated. Use the false default or a real boundary for the true case.
      struct Boundary : presonus::dsp::EQControlDrawBoundary {
        int released = 0, initialized = 0;
        void releaseBuffer() override { ++released; }
        void initBands(Presonus::EQControl &) override { ++initialized; }
      } boundary;
      x.bindPortableDrawBoundary(boundary);
      x.setBufferedDraw(flag);
      out = {U(x.isBufferedDraw())};
    } else
      return 2;
    for (auto v : out)
      std::cout << v << ' ';
    std::cout << '\n';
  }
}
