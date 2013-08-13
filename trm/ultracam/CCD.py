"""
Class to represent a CCD
"""
import matplotlib.cm as cm
from Window import *
from Uhead import *
from UErrors import *

class CCD(object):
    """
    Class to represent a CCD. Contains a list of Windows representing
    all the sub-windows of a CCD along with some extra defining
    attributes.

    Indexed access returns the component Window objects.
    """
    def __init__(self, wins, time, nxmax, nymax, good, head):
        """
        Creates a new CCD frame.
        
        Arguments:

        wins    -- list of non-overlapping Window objects.
        time    -- a Time representing the central time of the CCD.
        nxmax   -- maximum dimension in X, unbinned pixels.
        nymax   -- maximum dimension in Y, unbinned pixels.
        good    -- True if data are not junk.
        head    -- header. Must be None or a 'Uhead'
        """
        for win in wins:
            if not isinstance(win, Window):
                raise UltracamError('CCD.__init__: all windows must be Windows.')        

        if head is not None and not isinstance(head, Uhead):
            raise UltracamError('CCD.__init__: head should be a Uhead (or None).')        

        self._data = wins
        self.time  = time
        self.nxmax = nxmax
        self.nymax = nymax
        self.good  = good
        self.head  = head


    def __len__(self):
        """
        Returns the number of windows in the CCD
        """
        return len(self._data)

    def __eq__(self, other):
        """
        Equality of two CCDs is defined by matching binning factors, 
        maximum dimensions and windows (in order).
        """

        if self.nxmax != other.nxmax or self.nymax != other.nymax or len(self) != len(other): 
            return False
        
        # now test for equal windows
        for swin,owin in zip(self._data,other._data):
            if swin != owin:
                return False
        return True

    def __ne__(self, other):
        """
        Negation of equality operator.
        """
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __getitem__(self, i):
        """
        Returns data[i] where data is the internal ndarray data.
        """
        return self._data[i]

    def __setitem__(self, i, win):
        """
        Sets the i-th Window
        """
        if not isinstance(win, Window):
            raise UltracamError('CCD.__setitem__: win must be a Window')
        self._data[i] = win

    @property
    def data(self):
        """
        The list of Windows
        """
        return self._data

    @data.setter
    def data(self, wins):
        for win in wins:
            if not isinstance(win, Window):
                raise UltracamError('CCD.data: wins must be a list of Windows.')
        self._data = wins

    @property
    def nwin(self):
        """
        Returns the number of Windows (alternative to 'len')
        """
        return len(self._data)

    def anyInt(self):
        """
        Returns True if any of the contributing Windows are based on integers. It can be
        useful for memory and disk space reasons to keep data as 2-byte unsigned integers 
        but cause problems with arithematic operations. This allows you to check. 
        See also 'anyFloat', 'toFloat' and 'toInt'.
        """
        for win in self._data:
            if issubclass(win.dtype.type,np.integer):
                return True
        return False

    def anyFloat(self):
        """
        Returns True if any of the contributing Windows are based on floats. This is needed
        to evaluate the output type needed when writing to disk.
        """
        for win in self._data:
            if issubclass(win.dtype.type,np.floating):
                return True
        return False

    def toFloat(self, single=True):
        """
        Converts all Windows to a float type, either single or double
        precision.

        single  -- True to convert to 4-byte floats (else 8-byte)
        """
        for win in self._data:
            if single:
                win.totype(np.float32)
            else:
                win.totype(np.float64)

    def toInt(self):
        """
        Converts all Windows to an unsigned 2-byte integer type, rounding
        to the nearest integer. Warnings will be issued if data lies outside
        the 0 to 65535 range, but the conversion will proceed.
        """
        for win in self._data:
            if win.min() < 0 or win.max() > 65535:
                warnings.warn('CCD.toInt: input data out of range 0 to 65535')
            win.totype(np.uint16)
        
    def mean(self):
        """
        Returns the mean over all Windows of a CCD
        """
        nelem = 0
        sum   = 0.
        for win in self._data:
            nelem += win.size
            sum   += win.sum()
        return sum / float(nelem)

    def min(self):
        """
        Returns the minimum over all Windows of a CCD
        """
        minv = None
        for win in self._data:
            minv = win.min() if minv is None else min(minv, win.min())
        return minv

    def max(self):
        """
        Returns the maximum over all Windows of a CCD
        """
        maxv = None
        for win in self._data:
            maxv = win.max() if maxv is None else max(maxv, win.max())
        return maxv

    def npix(self):
        np = 0
        for win in self._data:
            np += win.size
        return np

    def median(self):
        """
        Returns median over all Windows of a CCD. 
        """

        # generate combined list of all pixels in CCD called 'arr'
        larr = []
        for win in self._data:
            larr.append(win.flatten())
        arr = np.concatenate(larr)

        return np.median(arr)


    def centile(self, pcent):
        """
        Returns percentile(s) over all Windows of a CCD. Given pcent, this
        routine returns the image level below which pcent percent of the pixel
        values lie.  pcent can be a single number or array-like. In the latter
        case a list of values is returned.

        pcent -- percentile or percentiles (array-like)

        Returns image value or values as a list equivalent to the input 
        percentiles. 
        """

        # check against a string which can look array-like
        if isinstance(pcent, basestring):
            raise UltracamError('CCD.centile: argument "pcent" cannot be a string')

        # generate combined list of all pixels in CCD called 'arr'
        larr = []
        for win in self._data:
            larr.append(win.flatten())
        arr = np.concatenate(larr)

        return np.percentile(arr,pcent)
    
    def rback(self):
        """
        Removes background from a CCD. Estimates
        background using a median of each window
        separately.
        """
        for win in self._data:
            win -= win.median()

    def plot(self, vmin, vmax, mpl=False, cmap=cm.binary):
        """
        Elementary intensity plot using either matplotlib's imshow 
        or pgplot's pggray. Typically some setup may be needed 
        before and after this. This one simply plots all windows
        using the Window.plot method

        vmin -- image value for lowest intensity
        vmax -- image value for highest intensity
        mpl  -- True for matplotlib, otherwise pgplot
        cmap -- colour map if mpl
        """
        for win in self._data:
            win.plot(vmin,vmax,mpl,cmap)

    def canCropTo(self, ccd):
        """
        Determines whether the CCD is croppable to the format of ccd.
        It does this by checking that each Window of ccd is enclosed
        by a Window of the CCD.
        """
        if self.nxmax != ccd.nxmax or self.nymax != ccd.nymax:
            return False

        for wino in ccd._data:
            for win in self._data:
                if win >= wino: break
            else:
                return False
        return True

    def cropTo(self, ccd):
        """
        Crops the CCD to match ccd returning the cropped
        CCD with the CCD itself unchanged. Raises an UltracamError 
        if it does not succeed.
        """
        if self.nxmax != ccd.nxmax or self.nymax != ccd.nymax:
            raise UltracamError('CCD.crop: maximum dimensions did not match')
        
        wins = []
        for nwino, wino in enumerate(ccd._data):
            for win in self._data:
                if win.canCropTo(wino):
                    wins.append(win.cropTo(wino))
                    break
            else:
                raise UltracamError('CCD.crop: could not crop any window of CCD to match window ' + 
                                    str(nwino+1) + ' of other.')
        return CCD(wins, self.time, self.nxmax, self.nymax, self.good, self.head)
        
    # arithematic
    def __iadd__(self, other):
        """
        Adds 'other' to the CCD in place (+=). 'other' can be a
        constant or a CCD
        """
        if isinstance(other, CCD):
            for win,owin in zip(self._data,other._data):
                win += owin
        else:
            for win in self._data:
                win += other
        return self

    def __isub__(self, other):
        """
        Subtracts 'other' from the CCD in place (-=)
        """
        if isinstance(other, CCD):
            for win,owin in zip(self._data,other._data):
                win -= owin
        else:
            for win in self._data:
                win -= other
        return self

    def __imul__(self, other):
        """
        Multiplies the CCD by 'other' in place (*=)
        """
        if isinstance(other, CCD):
            for win,owin in zip(self._data,other._data):
                win *= owin
        else:
            for win in self._data:
                win *= other
        return self

    def __idiv__(self, other):
        """
        Divides the CCD by 'other' in place (/=)
        """
        if isinstance(other, CCD):
            for win,owin in zip(self._data,other._data):
                win /= owin
        else:
            for win in self._data:
                win /= other
        return self

    def __add__(self, other):
        """
        Adds 'other' to the CCD (+)
        """
        twins = []
        if isinstance(other, CCD):
            for win,owin in zip(self._data,other._data):
                twins.append(win + owin)
        else:
            for win in self._data:
                twins.append(win + other)
        return CCD(twins, self.time, self.nxmax, self.nymax, self.good and other.good, self.head)

    def __sub__(self, other):
        """
        Subtracts 'other' from the CCD (-)
        """
        twins = []
        if isinstance(other, CCD):
            for win,owin in zip(self._data,other._data):
                twins.append(win - owin)
        else:
            for win in self._data:
                twins.append(win - other)
        return CCD(twins, self.time, self.nxmax, self.nymax, self.good and other.good, self.head)

    def __mul__(self, other):
        """
        Multiplies CCD by 'other' (*)
        """
        twins = []
        if isinstance(other, CCD):
            for win,owin in zip(self._data,other._data):
                twins.append(win * owin)
        else:
            for win in self._data:
                twins.append(win * other)
        return CCD(twins, self.time, self.nxmax, self.nymax, self.good and other.good, self.head)

    def __div__(self, other):
        """
        Divides CCD by 'other' (/)
        """
        twins = []
        if isinstance(other, CCD):
            for win,owin in zip(self._data,other._data):
                twins.append(win / owin)
        else:
            for win in self._data:
                twins.append(win / other)
        return CCD(twins, self.time, self.nxmax, self.nymax, self.good and other.good, self.head)

    def __radd__(self, other):
        """
        Defines other + CCD
        """
        twins = []
        for win in self._data:
            twins.append(other + win)
        return CCD(twins, self.time, self.nxmax, self.nymax, self.good and other.good, self.head)

    def __rsub__(self, other):
        """
        Defines other - CCD
        """
        twins = []
        for win in self._data:
            twins.append(other - win)
        return CCD(twins, self.time, self.nxmax, self.nymax, self.good and other.good, self.head)

    def __rmul__(self, other):
        """
        Defines other * CCD
        """
        twins = []
        for win in self._data:
            twins.append(other * win)
        return CCD(twins, self.time, self.nxmax, self.nymax, self.good and other.good, self.head)

    def __rdiv__(self, other):
        """
        Defines other * CCD
        """
        twins = []
        for win in self._data:
            twins.append(other / win)
        return CCD(twins, self.time, self.nxmax, self.nymax, self.good and other.good, self.head)

    def __str__(self):
        """
        Generates readable summary of a CCD
        """

        ret = ''
        if self.head is not None: ret += str(self.head)

        ret += '\nDimensions = ' + str(self.nxmax) + ', ' + str(self.nymax) + \
            ', number of windows = ' + str(len(self)) + ', status = ' + str(self.good) + '\n'

        for nwin,win in enumerate(self._data):
            ret += '\nWindow number ' + str(nwin+1) + ':\n'
            ret += str(win) + '\n'
        return ret

    def format(self):
        """
        Returns a string describing the format of the CCD
        """
        ret = ''
        for nwin, win in enumerate(self._data):
            ret += 'Window ' + str(nwin+1) + ' = ' + win.format() + '\n'
        return ret
