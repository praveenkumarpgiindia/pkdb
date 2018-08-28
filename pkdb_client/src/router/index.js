import Vue from 'vue'
import Router from 'vue-router'
import Home from '@/components/Home'
import References from '@/components/References'
import About from '@/components/About'
import Studies from '@/components/Studies'


Vue.use(Router)

export default new Router({
    routes: [
        {
            path: '/',
            name: 'Home',
            component: Home
        },
        {
            path: '/references',
            name: 'References',
            component: References
        },
        {
            path: '/about',
            name: 'About',
            component: About
        },
        {
            path: '/studies',
            name: 'Studies',
            component: Studies
        },
    ]
})