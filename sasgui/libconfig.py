import sastool.libconfig

def qunit():
    if sastool.libconfig.LENGTH_UNIT=='nm':
        return u'nm$^{-1}$'
    elif sastool.libconfig.LENGTH_UNIT=='A':
        return u'\xc5$^{-1}$'
    else:
        raise NotImplementedError('Invalid length unit: '+str(sastool.libconfig.LENGTH_UNIT))
    
