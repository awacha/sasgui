import sastool.libconfig

def qunit():
    if sastool.libconfig.LENGTH_UNIT=='nm':
        return 'nm$^{-1}$'
    elif sastool.libconfig.LENGTH_UNIT=='A':
        return '\xc5$^{-1}$'
    else:
        raise NotImplementedError('Invalid length unit: '+str(sastool.libconfig.LENGTH_UNIT))
    
__all__=['qunit']
