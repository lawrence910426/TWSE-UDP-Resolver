#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>
#include "parser.h"

namespace py = pybind11;

PYBIND11_MODULE(twse_udp_resolver, m) {
    m.doc() = "TWSE UDP Resolver (Python interface)"; // optional module docstring

    py::class_<Parser>(m, "Parser")
        .def(py::init<>())
        .def("start_loop", &Parser::start_loop, "Start the UDP stream parsing loop")
        .def("end_loop", &Parser::end_loop, "Stop the parsing loop")
        .def("set_multicast", &Parser::set_multicast, "Sets the parameter of multicast");
}