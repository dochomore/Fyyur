#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from distutils import errors
import enum
import json
from datetime import datetime
import logging
from logging import FileHandler, Formatter
from msilib.schema import Error
from unicodedata import name

import babel
import dateutil.parser
from flask import (Flask, Response, flash, redirect, render_template, request,
                   url_for, jsonify)
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import Form

import config
from forms import *

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db=db)

app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = config.SECRET_KEY

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(1024))
    facebook_link = db.Column(db.String(1024))
    website_link = db.Column(db.String(1024), default='')
    seeking_talent = db.Column(db.Boolean(), default=False)
    seeking_description = db.Column(db.String(), default='')
    show = db.relationship('Show', backref='venue',
                           lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'{self.name} - {self.city}, {self.state}'


class Show(db.Model):
    __tablename__ = 'shows'

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    artist_id = db.Column(
        db.Integer, db.ForeignKey('Artist.id'), nullable=False)

    def __repr__(self) -> str:
        return f'show start time {self.start_time}'


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(1024))
    facebook_link = db.Column(db.String(1024))
    show = db.relationship('Show', backref='artist',
                           lazy=True, cascade="all, delete-orphan")
    website_link = db.Column(db.String(1024), default='')
    seeking_venue = db.Column(db.Boolean(), default=False)
    seeking_description = db.Column(db.String(), default='')

    def __repr__(self) -> str:
        return f'{self.name} {self.city, self.state}'

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    venue_query = db.session.query(Venue.state, Venue.city).group_by(
        Venue.state, Venue.city).all()
    list_of_venues = []

    for dt in venue_query:
        venues_query = db.session.query(Venue.id, Venue.name).filter(
            Venue.state == dt[0]).filter(Venue.city == dt[1]).all()
        venues = []
        for v in venues_query:
            count = db.session.query(Show).filter(
                Show.venue_id == v[0]).filter(Show.start_time > datetime.now()).count()
            venues.append({'id': v[0], 'name': v[1],
                          'num_upcomming_shows': count})

        list_of_venues.append(
            {'state': dt[0], 'city': dt[1], 'venues': venues})

    return render_template('pages/venues.html', areas=list_of_venues)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    response = {}
    keyword = request.form.get('search_term')
    if keyword:
        search = "%{}%".format(keyword)
        venues = Venue.query.filter(Venue.name.ilike(search)).all()
        response['count'] = len(venues)
        data = []
        for v in venues:
            upcoming_shows = db.session.query(Show).join(
                Venue, Show.id == v.id).filter(Show.start_time > datetime.now()).count()
            data.append({'id': v.id, 'name': v.name,
                        'num_upcoming_show': upcoming_shows})
        response['data'] = data
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/shows/search', methods=['POST'])
def search_shows():
    response = {}
    keyword = request.form.get('search_term')
    if keyword:
        search = "%{}%".format(keyword)
        shows = db.session.query(Artist.id.label('id'), Artist.name.label('artist_name'), Venue.name.label('venue_name'), Show.start_time.label(
            'start_time')).join(Show, Show.id == Artist.id).join(Venue, Show.venue_id == Venue.id).filter(Artist.name.ilike(search)).all()
        data = []
        response['count'] = len(shows)
        for show in shows:
            dict_show = dict(show)
            dict_show["start_time"] = dict_show['start_time'].strftime(
                "%Y-%m-%dT%H:%M:%S%Z")
            data.append(dict_show)

        response['data'] = data
    return render_template('pages/search_shows.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/shows/<int:show_id>', methods=['GET'])
def show_detail(show_id):
    result = db.session.query(Artist.id.label('id'), Artist.name.label('artist_name'), Artist.image_link.label('artist_image_link'), Artist.city.label(
        'city'), Venue.name.label('venue_name'), Show.start_time.label('start_time')).join(Show, Show.id == Artist.id).join(Venue, Show.venue_id == Venue.id).all()
    shows = []
    for show in result:
        dict_show = dict(show)

        dict_show["start_time"] = dict_show['start_time'].strftime(
            "%Y-%m-%dT%H:%M:%S%Z")

        shows.append(dict_show)

    return render_template('pages/show.html', shows=shows)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = db.session.query(Venue).get(venue_id)
    dt = []
    if venue:
        data = {'id': venue.id,
                'name': venue.name,
                'address': venue.address,
                'city': venue.city,
                'state': venue.state,
                'phone': venue.phone,
                'website': venue.website_link,
                'facebook_link': venue.facebook_link,
                'seeking_talent': venue.seeking_talent,
                'seeking_description': venue.seeking_description,
                'image_link': venue.image_link}

        # past show
        past_show_list = db.session.query(Artist.id.label('artist_id'),
                                          Artist.name.label('artist_name'), Artist.image_link.label(
            'artist_image_link'),
            Show.start_time.label('start_time'), ).join(Artist, Show.artist_id == Artist.id).filter(Show.start_time < datetime.now()).all()

        past_show = []
        for us in past_show_list:
            dict_ps = dict(us)
            dict_ps["start_time"] = dict_ps['start_time'].strftime(
                "%Y-%m-%dT%H:%M:%S%Z")
            past_show.append(dict_ps)
        data['past_shows'] = past_show
        data['past_shows_count'] = len(past_show)

        # upcoming shows
        upcoming_shows_list = db.session.query(Artist.id.label('artist_id'),
                                               Artist.name.label('artist_name'), Artist.image_link.label(
            'artist_image_link'),
            Show.start_time.label('start_time'), ).join(Artist, Show.artist_id == Artist.id).filter(Show.start_time > datetime.now()).all()

        upcoming_show = []
        for us in upcoming_shows_list:
            dict_ps = dict(us)
            dict_ps["start_time"] = dict_ps['start_time'].strftime(
                "%Y-%m-%dT%H:%M:%S%Z")
            upcoming_show.append(dict_ps)
        data['upcoming_shows'] = upcoming_show
        data['upcoming_shows_count'] = len(upcoming_show)

        dt.append(data)
    response = list(filter(lambda d: d['id'] ==
                           venue_id, dt))[0]
    return render_template('pages/show_venue.html', venue=response)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    try:
        form = VenueForm()
        if form.errors.get('phone'):
            flash('validation error, invalid phone format')
        elif form.errors:
            flash(f'validation error')

        if form.validate_on_submit():
            venue = Venue(name=form.name.data,
                          city=form.city.data,
                          state=form.state.data,
                          address=form.address.data,
                          phone=form.phone.data,
                          image_link=form.image_link.data,
                          facebook_link=form.facebook_link.data,
                          website_link=form.website_link.data,
                          seeking_talent=form.seeking_talent.data,
                          seeking_description=form.seeking_description.data)
            data = db.session.add(venue)
            db.session.commit()
            flash('Venue ' + form.name.data +
                  ' was successfully listed!')
        else:
            flash('validation error')
    except:
        flash('An error occurred. Venue ' +
              data.name + ' could not be listed.')

        db.session.rollback()
    finally:
        db.session.close()
    return render_template('pages/home.html')


@app.route('/venues/<int:venue_id>', methods=['DELETE', 'POST'])
def delete_venue(venue_id):
    try:

        venue = Venue.query.get(venue_id)
        if venue:
            db.session.delete(venue)
            db.session.commit()
            flash('sucesfully deleted')
        else:
            raise Exception()
    except:
        flash('something went wrong. venue might be referenced in Show')
        db.session.rollback()
    finally:
        db.session.close()

    return redirect(url_for('index'))
#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    data = Artist.query.all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    response = {}
    keyword = request.form.get('search_term')
    if keyword:
        search = "%{}%".format(keyword)
        artists = Artist.query.filter(Artist.name.ilike(search)).all()
        response['count'] = len(artists)
        data = []
        for artist in artists:
            upcoming_shows = db.session.query(Show).join(
                Artist, Show.id == artist.id).filter(Show.start_time > datetime.now()).count()
            data.append({'id': artist.id, 'name': artist.name,
                        'num_upcoming_show': upcoming_shows})
        response['data'] = data

    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = db.session.query(Artist).get(artist_id)
    dt = []
    if artist:
        data = {'id': artist.id,
                'name': artist.name,
                'genres': artist.genres,
                'city': artist.city,
                'state': artist.state,
                'phone': artist.phone,
                'website': artist.website_link,
                'facebook_link': artist.facebook_link,
                'seeking_venue': artist.seeking_venue,
                'seeking_description': artist.seeking_description,
                'image_link': artist.image_link}

        # past show
        past_show_list = db.session.query(Venue.id.label('venue_id'),
                                          Venue.name.label('venue_name'), Venue.image_link.label(
            'venue_image_link'),
            Show.start_time.label('start_time'), ).join(Venue, Show.venue_id == Venue.id).filter(Show.start_time < datetime.now()).all()

        past_show = []
        for us in past_show_list:
            dict_ps = dict(us)
            dict_ps["start_time"] = dict_ps['start_time'].strftime(
                "%Y-%m-%dT%H:%M:%S%Z")
            past_show.append(dict_ps)
        data['past_shows'] = past_show
        data['past_shows_count'] = len(past_show)

        # upcoming shows
        upcoming_shows_list = db.session.query(Venue.id.label('venue_id'),
                                               Venue.name.label('venue_name'), Venue.image_link.label(
                                                   'venue_image_link'),
                                               Show.start_time.label(
                                                   'start_time'),
                                               ).join(Venue, Show.venue_id == Venue.id).filter(Show.start_time > datetime.now()).all()

        upcoming_show = []
        for us in upcoming_shows_list:
            dict_ps = dict(us)
            dict_ps["start_time"] = dict_ps['start_time'].strftime(
                "%Y-%m-%dT%H:%M:%S%Z")
            upcoming_show.append(dict_ps)
        data['upcoming_shows'] = upcoming_show
        data['upcoming_shows_count'] = len(upcoming_show)
        dt.append(data)

    response = list(filter(lambda d: d['id'] ==
                           artist_id, dt))[0]
    return render_template('pages/show_artist.html', artist=response)

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    try:
        form = ArtistForm()
        artist = db.session.query(Artist).get(artist_id)
        if artist:
            form.name.data = artist.name
            form.phone.data = artist.phone
            form.genres.data = artist.genres
            form.city.data = artist.city
            form.state.data = artist.state
            form.phone.data = artist.phone
            form.website_link.data = artist.website_link
            form.facebook_link.data = artist.facebook_link
            form.seeking_venue.data = artist.seeking_venue
            form.seeking_description.data = artist.seeking_description
            form.image_link.data = artist.image_link

        else:
            raise Exception()
    except:
        db.session.rollback()
    finally:
        db.session.close()

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    try:
        form = ArtistForm()
        if form.validate_on_submit():
            artist = Artist.query.get(artist_id)
            artist.name = form.name.data
            artist.city = form.city.data
            artist.state = form.state.data
            artist.phone = form.phone.data
            artist.genres = form.genres.data
            artist.image_link = form.image_link.data
            artist.facebook_link = form.facebook_link.data
            artist.website_link = form.website_link.data
            artist.seeking_venue = form.seeking_venue.data
            artist.seeking_description = form.seeking_description.data
            db.session.commit()
            flash('updated successfully')
        else:
            flash('something went wrong!')
    except:
        flash('something went wrong!')
        db.session.rollback()
    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    try:
        form = VenueForm()
        venue = db.session.query(Venue).get(venue_id)
        if venue:
            form.name.data = venue.name
            form.phone.data = venue.phone
            form.address.data = venue.address
            form.city.data = venue.city
            form.state.data = venue.state
            form.website_link.data = venue.website_link
            form.facebook_link.data = venue.facebook_link
            form.seeking_talent.data = venue.seeking_talent
            form.seeking_description.data = venue.seeking_description
            form.image_link.data = venue.image_link
        else:
            raise Exception()
    except:
        db.session.rollback()
    finally:
        db.session.close()
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    try:
        form = VenueForm()
        if form.validate_on_submit():
            venue = Venue.query.get(venue_id)
            venue.name = form.name.data
            venue.city = form.city.data
            venue.state = form.state.data
            venue.address = form.address.data
            venue.phone = form.phone.data
            venue.image_link = form.image_link.data
            venue.facebook_link = form.facebook_link.data
            venue.website_link = form.website_link.data
            venue.seeking_talent = form.seeking_talent.data
            venue.seeking_description = form.seeking_description.data
            db.session.commit()
            flash('updated successfully')
        else:
            flash('something went wrong!')
    except:
        flash('something went wrong!')
        db.session.rollback()
    finally:
        db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = ArtistForm(request.form)
    if form.validate_on_submit() == False:
        raise Exception(form.errors)
    try:
       # called upon submitting the new artist listing form

        if form.errors.get('phone'):
            flash('validation error, invalid phone format')

        elif form.errors.get('facebook_link'):
            flash(f'validation error, facebook address is out of specified list.')

        elif form.errors:
            flash(f'validation error {form.errors}')
        data = ''
        if form.validate_on_submit():
            artist = Artist(name=form.name.data,
                            city=form.city.data,
                            state=form.state.data,
                            phone=form.phone.data,
                            genres=form.genres.data,
                            image_link=form.image_link.data,
                            facebook_link=form.facebook_link.data,
                            website_link=form.website_link.data,
                            seeking_venue=form.seeking_venue.data,
                            seeking_description=form.seeking_description.data
                            )
            data = db.session.add(artist)
            db.session.commit()

            # on successful db insert, flash success
            flash('Artist ' + request.form['name'] +
                  ' was successfully listed!')
        else:
            flash('validation error')
    except:
        flash('An error occurred. Artist ' +
              form.name.data + ' could not be listed.')
        db.session.rollback()
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    shows = db.session.query(
        Venue.id.label('venue_id'),
        Venue.name.label('venue_name'),
        Artist.id.label('artist_id'),
        Artist.name.label('artist_name'),
        Artist.image_link.label('artist_image_link'),
        Show.start_time).join(
        Artist, Artist.id == Show.artist_id).join(Venue, Venue.id == Show.venue_id).all()

    data = []
    for show in shows:
        dict_show = dict(show)
        st = dict_show.get('start_time').strftime("%Y-%m-%dT%H:%M:%S%Z")
        dict_show['start_time'] = st
        data.append(dict_show)
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    try:
        form = ShowForm()
        if form.validate_on_submit():
            db.session.add(Show(
                start_time=form.start_time.data,
                venue_id=form.venue_id.data,
                artist_id=form.artist_id.data))
            db.session.commit()
            flash('Show was successfully listed!')
    except Exception:
        flash(f'An error occurred. Show could not be listed.')
        db.session.rollback()
    finally:
        db.session.close()
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
