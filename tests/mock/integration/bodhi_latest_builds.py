# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from munch import Munch

BODHI_LATEST_BUILDS = Munch(
    {
        "f28-updates-candidate": "colin-0.3.1-1.fc28",
        "f29-updates-candidate": "colin-0.3.1-1.fc29",
        "f30-updates-candidate": "colin-0.3.1-2.fc30",
        "f27-updates-candidate": "colin-0.2.0-1.fc27",
        "f28-updates-testing": "colin-0.3.1-1.fc28",
        "f29-updates-testing": "colin-0.3.1-1.fc29",
        "f27-updates-testing": "colin-0.2.0-1.fc27",
        "f30-updates-testing": "colin-0.3.1-2.fc30",
        "f28-updates": "colin-0.3.1-1.fc28",
        "f29-updates": "colin-0.3.1-1.fc29",
        "f27-updates": "colin-0.2.0-1.fc27",
        "f30-updates": "colin-0.3.1-2.fc30",
        "f28-override": "colin-0.3.1-1.fc28",
        "f29-override": "colin-0.3.1-1.fc29",
        "f27-override": "colin-0.2.0-1.fc27",
        "f30-override": "colin-0.3.1-2.fc30",
        "f28-updates-testing-pending": "colin-0.3.1-1.fc28",
        "f29-updates-testing-pending": "colin-0.3.1-1.fc29",
        "f27-updates-testing-pending": "colin-0.0.4-3.fc27",
        "f30-updates-testing-pending": "colin-0.3.1-2.fc30",
        "f28-updates-pending": "colin-0.3.1-1.fc28",
        "f29-updates-pending": "colin-0.3.1-1.fc29",
        "f27-updates-pending": "colin-0.2.0-1.fc27",
        "f30-updates-pending": "colin-0.3.1-2.fc30",
    }
)
